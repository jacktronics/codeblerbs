#!/usr/bin/env python3
"""
This program is designed to clean your macOS network stack after a failed/crash F5 Web VPN session. 

The F5 VPN main software called SVPN under the hood can in some circumstances freeze and require a force quit / SIGKILL, 
This leaves bad routes in place, bad host file entries and wrong DNS settings in SystemConfiguration (accessible via scutil in cli)

This tool makes use of SYSCTL, IOCTL, LibC and PyObjC-Framework-SystemConfiguration in order to clean the system without reboot.

This program requires the pyobjc-framework-SystemConfiguration module, it MUST be executed with root permissions.
"""
import fcntl, socket, ctypes, enum, os, sys, time
from SystemConfiguration import SCDynamicStoreCreate, \
								SCDynamicStoreCopyValue, \
								SCDynamicStoreRemoveValue, \
								kCFAllocatorDefault

F5APP_IPV4_CONFSTR = 'State:/Network/Service/F5NetworksServicePPP/IPv4'
F5APP_DNS_CONFSTR = 'State:/Network/Service/F5NetworksServicePPP/DNS'
IFACE_SCCONFIG_PATH = 'State:/Network/Interface'
SVPN_HOST_FILE_BACKUP_PATH = '/private/etc/.hosts.bkp'
STD_HOST_FILE_PATH = '/private/etc/hosts'

IF_NAMESIZE = 16
MAXHOSTNAMELEN = 256
SIOCGIFFLAGS = 0xc0206911
SIOCSIFFLAGS = 0x80206910

class RTF(enum.Enum):
	UP = 0x1, "U"
	GATEWAY = 0x2, "G"
	HOST = 0x4, "H"
	REJECT = 0x8, "R"
	DYNAMIC = 0x10, "D"
	MODIFIED = 0x20, "M"
	DONE = 0x40, "d"
	DELCLONE = 0x80, ""
	CLONING = 0x100, "C"
	XRESOLVE = 0x200, "X"
	LLINFO = 0x400, "L"
	STATIC = 0x800, "S"
	BLACKHOLE = 0x1000, "B"
	NOIFREF = 0x2000, ""
	PROTO2 = 0x4000, "1"
	PROTO1 = 0x8000, "2"
	PRCLONING = 0x10000, "c"
	WASCLONED = 0x20000, "W"
	PROTO3 = 0x40000, "3"
	PINNED = 0x100000, ""
	LOCAL = 0x200000, ""
	BROADCAST = 0x400000, "b"
	MULTICAST = 0x800000, "m"
	IFSCOPE = 0x1000000, "I"
	CONDEMNED = 0x2000000, ""
	IFREF = 0x4000000, "i"
	PROXY = 0x8000000, "Y"
	ROUTER = 0x10000000, "r"
	DEAD = 0x20000000, ""
	GLOBAL = 0x40000000, "g"
	def __eq__(self, other) -> bool:
		if self.__class__ is other.__class__:
			return self.value == other.value
		return NotImplemented
	def __rand__(self, other) -> bool:
		if self.__class__ is other.__class__:
			return self.value & other.value
		if other.__class__ == int:
			return self.value & other
		return NotImplemented
	def __or__(self, other) -> bool:
		if self.__class__ is other.__class__:
			return self.value | other.value
		if other.__class__ == int:
			return self.value | other
		return NotImplemented
	def __add__(self, other) -> bool:
		if self.__class__ is other.__class__:
			return self.value + other.value
		if other.__class__ == int:
			return self.value + other
		return NotImplemented
	def __new__(cls, value, flag) -> object:
		member = object.__new__(cls)
		member._value_ = value
		member.flag = flag
		return member
	def __int__(self) -> int:
		return self.value

def RTF_LIST(mask: ctypes.c_int, flags: enum.Enum = RTF) -> list:
    return [flag for flag in flags if mask & flag.value]

def RTF_LIST_STR(flags: list) -> str:
	s = str()
	for f in flags:
		s = f"{s}{f.flag}"
	return s

class RTM(enum.IntEnum):
	ADD = 0x1
	DELETE = 0x2
	CHANGE = 0x3
	GET = 0x4
	LOSING = 0x5
	REDIRECT = 0x6
	MISS = 0x7
	LOCK = 0x8
	OLDADD = 0x9
	OLDDEL = 0xa
	RESOLVE = 0xb
	NEWADDR = 0xc
	DELADDR = 0xd
	IFINFO = 0x10
	NEWMADDR = 0xf
	DELMADDR = 0xa
	IFINFO2 = 0x12
	NEWMADDR2 = 0x13
	GET2 = 0x14

class AF(enum.IntEnum):
	UNSPEC = 0
	UNKNWN = 255
	INET = 2
	APPLETALK = 16
	LINK = 18
	INET6 = 30

class RTA(enum.IntEnum):
	DST = 0x1
	GATEWAY = 0x2
	NETMASK = 0x4
	GENMASK = 0x8
	IFP = 0x10
	IFA = 0x20
	AUTHOR = 0x40
	BRD = 0x80

class NI(enum.IntEnum):
	NOFQDN = 0x1
	NUMERICHOST = 0x2
	NAMEREQD = 0x4
	NUMERICSERV = 0x8
	NUMERICSCOPE = 0x100
	DGRAM = 0x10
	WITHSCOPEID = 0x20

class in_addr(ctypes.BigEndianStructure):
	_fields_ = [("s_addr", ctypes.c_uint32)]

class sockaddr_in(ctypes.Structure):
	_fields_ = [("sin_len", ctypes.c_uint8),
				("sin_family", ctypes.c_uint8),
				("sin_port", ctypes.c_uint16),
				("sin_addr", in_addr),
				("sin_zero", ctypes.c_char * 8)] 

class in6_addr(ctypes.BigEndianStructure):
	_fields_ = [("s6_addr", ctypes.c_ubyte * 16)]

class sockaddr_in6(ctypes.Structure):
	_fields_ = [("sin6_len", ctypes.c_uint8),
				("sin6_family", ctypes.c_uint8),
				("sin6_port", ctypes.c_uint16),
				("sin6_flowinfo", ctypes.c_uint32),
				("sin6_addr", in6_addr),
				("sin6_scope_id", ctypes.c_uint32)]

class socketaddr(ctypes.Structure):
	_fields_ = [("sa_len", ctypes.c_uint8),
			("sa_family", ctypes.c_uint8),
			("sa_data", ctypes.c_char * 14)] #sa_data can be longer, but we're re-casting into another struct later ...

class rt_metrics(ctypes.Structure):
	_fields_ = [("rmx_locks", ctypes.c_uint32),
				("rmx_mtu", ctypes.c_uint32),
				("rmx_hopcount", ctypes.c_uint32),
				("rmx_expire", ctypes.c_int32),
				("rmx_recvpipe", ctypes.c_uint32),
				("rmx_sendpipe", ctypes.c_uint32),
				("rmx_ssthresh", ctypes.c_uint32),
				("rmx_rtt", ctypes.c_uint32),
				("rmx_rttvar", ctypes.c_uint32),
				("rmx_pksent", ctypes.c_uint32),
				("rmx_state", ctypes.c_uint32),
				("rmx_filler", ctypes.c_uint32 * 3)]

class rt_msg(ctypes.Structure):
    _fields_ = [("rtm_msglen", ctypes.c_ushort),
                ("rtm_version", ctypes.c_ubyte),
                ("rtm_type", ctypes.c_ubyte),
                ("rtm_index", ctypes.c_ushort),
                ("rtm_flags", ctypes.c_int),
                ("rtm_addrs", ctypes.c_int),
                ("rtm_pid", ctypes.c_uint32),
                ("rtm_seq", ctypes.c_int),
                ("rtm_errno", ctypes.c_int),
                ("rtm_use", ctypes.c_int),
                ("rtm_inits", ctypes.c_uint32),
                ("rtm_rmx", rt_metrics)]

class ifreq_ifflags(ctypes.Structure):
	_fields_ = [("ifr_name", ctypes.c_char * IF_NAMESIZE),
				("ifru_flags", ctypes.c_ushort)]

def ROUNDUP(addr: ctypes.c_ubyte, int_sz: int = ctypes.sizeof(ctypes.c_int())) -> int:
	if addr > 0:
		return 1 + ((addr - 1) | (int_sz - 1))
	else:
		return int_sz

def structFromByteArray(b: bytes, l: ctypes.c_ubyte, s: ctypes.Structure) -> ctypes.Structure:
	blob = ctypes.create_string_buffer(ctypes.sizeof(s()))
	exit_code = ctypes.memmove(blob, b, l)
	return s.from_buffer_copy(blob)

def getNameInfo(sockaddr: ctypes.Structure, l: ctypes.c_ubyte) -> str:
	info_flags = NI.WITHSCOPEID | NI.NUMERICHOST
	info_blob = ctypes.create_string_buffer(MAXHOSTNAMELEN)
	exit_code = libc.getnameinfo(ctypes.byref(sockaddr), l, ctypes.byref(info_blob), ctypes.sizeof(info_blob), None, 0, info_flags)
	return info_blob.value.decode('utf-8')

def prefixFromMaskBytes(mask: bytes) -> int:
	prefix = 0
	for c in mask:
		prefix = prefix + bin(c).count("1")
	return prefix

def NET_RT_DUMP() -> tuple[bytes, int]:
	CTL_NET = 4
	PF_ROUTE = 17
	NET_RT_DUMP = 1
	NET_RT_DUMP_ARGC = 6
	# sysctl NET_RT_DUMP call definition
	NET_RT_DUMP_CALL = ( ctypes.c_int * NET_RT_DUMP_ARGC )( CTL_NET, PF_ROUTE, 0, 0, NET_RT_DUMP, 0 )
	# we do not know the payload size, so we have to call a first time to get it, allocate the return buffer with the size and a second time for the payload ...
	rt_dump_size = ctypes.c_size_t()
	result = libc.sysctl(NET_RT_DUMP_CALL, NET_RT_DUMP_ARGC, None, ctypes.byref(rt_dump_size), None, ctypes.c_size_t(0))
	rt_dump_blob = ctypes.create_string_buffer(rt_dump_size.value)
	result = libc.sysctl(NET_RT_DUMP_CALL, NET_RT_DUMP_ARGC, ctypes.byref(rt_dump_blob), ctypes.byref(rt_dump_size), None, ctypes.c_size_t(0))
	return ( rt_dump_blob.raw, rt_dump_size.value )

def ROUTE_DELETE(rt_msghdr: ctypes.Structure, rt_dump_bytes: bytes, msg_idx: int, rt_sock: socket.socket, rt_seqno: int) -> tuple[bool, int]:
	msg_end = msg_idx + rt_msghdr.rtm_msglen
	rt_msghdr.rtm_type = RTM.DELETE
	rt_msghdr.rtm_seq = rt_seqno
	del_rt_msghdr = bytearray(rt_msghdr)
	del_rtmsg = bytearray(rt_dump_bytes[msg_idx+ctypes.sizeof(rt_msghdr):msg_end])
	del_rtmsg[0:0] = del_rt_msghdr
	ret = os.write(rt_sock.fileno(), bytes(del_rtmsg))
	if ret > 0:
		rt_seqno = rt_seqno + 1
		return ( True, rt_seqno )
	else: return ( False, rt_seqno )

def set_if_state(ifname:str, desired_up_state:bool) -> None:
	ifreq_get = ifreq_ifflags(bytes(ifname, 'utf-8'), 0)
	s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
	gif_result = fcntl.ioctl(s.fileno(), SIOCGIFFLAGS, bytes(ifreq_get))
	ifreq_gif_res = ifreq_ifflags.from_buffer_copy(gif_result)
	ifflags = ifreq_gif_res.ifru_flags
	if not desired_up_state and (ifflags & 1):
		ifflags -= 1
		ifreq_sif = ifreq_ifflags(bytes(ifname, 'utf-8'), ifflags)
		sif_result = fcntl.ioctl(s.fileno(), SIOCSIFFLAGS, bytes(ifreq_sif))
	elif desired_up_state and (ifflags | 0):
		ifflags += 1
		ifreq_sif = ifreq_ifflags(bytes(ifname, 'utf-8'), ifflags)
		sif_result = fcntl.ioctl(s.fileno(), SIOCSIFFLAGS, bytes(ifreq_sif))

if os.getuid() != 0:
	full_command = 'sudo'
	for arg in sys.argv:
		full_command = f'{full_command} {arg}'
	sys.exit(f'\U0000274c You must run this script with root permission, like this : "{full_command}"')

libc = ctypes.CDLL('libc.dylib')

# route mod socket
rt_sock = socket.socket(socket.AF_ROUTE, socket.SOCK_RAW, socket.AF_UNSPEC)
rt_sock.setsockopt(socket.SOL_SOCKET, socket.SO_USELOOPBACK, 1)
# route socket sequence number initialization 
rt_seqno = 0

rt_dump_bytes, rt_dump_size = NET_RT_DUMP()

idx = 0
defaultGw = False

while idx < rt_dump_size:
	rt_message = rt_msg.from_buffer_copy(rt_dump_bytes[idx:])
	iface_blob = ctypes.create_string_buffer(IF_NAMESIZE+1)
	exit_code = libc.if_indextoname(rt_message.rtm_index, ctypes.byref(iface_blob))
	iface = iface_blob.value.decode('utf-8')
	curent_msg_idx = idx
	sa_idx = idx + ctypes.sizeof(rt_message)
	#incrementing idx early so we can skip RT_MSG's we do not need
	idx = idx + rt_message.rtm_msglen
	if rt_message.rtm_flags & ( RTF.HOST | RTF.GATEWAY ) == ( RTF.HOST | RTF.GATEWAY ) :
		continue
	if_idx = 1
	while if_idx < rt_message.rtm_addrs:
		if if_idx & rt_message.rtm_addrs:
			rta_flag = RTA(if_idx)
			sockaddr_bytes = rt_dump_bytes[sa_idx:]
			sa = socketaddr.from_buffer_copy(sockaddr_bytes)
			sa_idx = sa_idx + ROUNDUP(sa.sa_len)
			if rta_flag == RTA.DST:
				# RTA.DST comes first, and subsequent struct may not set the family so we set it here
				family = AF(sa.sa_family)
				if family == AF.INET:
					sin = structFromByteArray(sockaddr_bytes, sa.sa_len, sockaddr_in)
					destination = getNameInfo(sin, sin.sin_len)
					if (sin.sin_addr.s_addr == 0):
						defaultGw = True
				elif family == AF.INET6:
					sin6 = structFromByteArray(sockaddr_bytes, sa.sa_len, sockaddr_in6)
					destination = getNameInfo(sin6, sin6.sin6_len)
					if destination == '::':
						defaultGw = True
			elif rta_flag == RTA.NETMASK:
				if family == AF.INET:
					sin = structFromByteArray(sockaddr_bytes, sa.sa_len, sockaddr_in)
					prefix = prefixFromMaskBytes([ sin.sin_addr.s_addr ])
				elif family == AF.INET6:
					sin6 = structFromByteArray(sockaddr_bytes, sa.sa_len, sockaddr_in6)
					if sin6.sin6_len > 0:
						prefix = prefixFromMaskBytes(sin6.sin6_addr.s6_addr)
			elif rta_flag == RTA.GATEWAY:
				if family == AF.INET:
					sin = structFromByteArray(sockaddr_bytes, sa.sa_len, sockaddr_in)
					gw = getNameInfo(sin, sin.sin_len)
				elif family == AF.INET6:
					sin6 = structFromByteArray(sockaddr_bytes, sa.sa_len, sockaddr_in6)
					gw = getNameInfo(sin6, sin6.sin6_len)
		if_idx = if_idx << 1
	if rt_message.rtm_flags & RTF.LLINFO :
		network = destination
	elif defaultGw:
		defaultGw = False
		network = 'default'
	else:
		network = f"{destination}/{prefix}"
	route = f"{network} via {gw} flags {RTF_LIST_STR(RTF_LIST(rt_message.rtm_flags))} iface {iface} "
	if ( rt_message.rtm_flags & RTF.GATEWAY ) and not ( rt_message.rtm_flags & RTF.GLOBAL ):
		print(f'\U000023f3 Removing route {route}')
		ret, rt_seqno = ROUTE_DELETE(rt_message, rt_dump_bytes, curent_msg_idx, rt_sock, rt_seqno)
		continue
	if gw == '1.1.1.1' or destination == '1.1.1.1':
		print(f'\U000023f3 Removing route {route}')
		ret, rt_seqno = ROUTE_DELETE(rt_message, rt_dump_bytes, curent_msg_idx, rt_sock, rt_seqno)
		continue

# if f5 svpn host file backup is found, renaming it to standard host file location
if os.path.isfile(SVPN_HOST_FILE_BACKUP_PATH):
	print(f'\U000023f3 Deleting corrupted SVPN generated host file at {STD_HOST_FILE_PATH}')
	os.remove(STD_HOST_FILE_PATH)
	print(f'\U000023f3 Renaming {SVPN_HOST_FILE_BACKUP_PATH} as {STD_HOST_FILE_PATH}')
	os.rename(SVPN_HOST_FILE_BACKUP_PATH, STD_HOST_FILE_PATH)

# finding F5 SVPN PPP device configs and deleting them
ds = SCDynamicStoreCreate(kCFAllocatorDefault, "systemConfigurationSearch", None, None)
f5ppp_ipv4 = SCDynamicStoreCopyValue(ds, F5APP_IPV4_CONFSTR)
if f5ppp_ipv4:
	print(f'\U000023f3 Deleting Config {F5APP_IPV4_CONFSTR}')
	was_deleted = SCDynamicStoreRemoveValue(ds, F5APP_IPV4_CONFSTR)
f5ppp_dns = SCDynamicStoreCopyValue(ds, F5APP_DNS_CONFSTR)
if f5ppp_dns:
	print(f'\U000023f3 Deleting Config {F5APP_DNS_CONFSTR}')
	was_deleted = SCDynamicStoreRemoveValue(ds, F5APP_DNS_CONFSTR)

time.sleep(.1)
iface_name_list = []
ifaces = SCDynamicStoreCopyValue(ds, IFACE_SCCONFIG_PATH)
for i in ifaces['Interfaces']:
	link_state = SCDynamicStoreCopyValue(ds, f'{IFACE_SCCONFIG_PATH}/{i}/Link')
	has_ipv4 = SCDynamicStoreCopyValue(ds, f'{IFACE_SCCONFIG_PATH}/{i}/IPv4')
	if link_state and link_state['Active'] and not ( has_ipv4 == None ):
		print(f'\U000023f3 Resetting {i} ...')
		set_if_state(i, False)
		time.sleep(.1)
		set_if_state(i, True)

print('\U00002705 Success')
