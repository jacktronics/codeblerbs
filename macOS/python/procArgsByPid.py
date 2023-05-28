#!/usr/bin/env python3
"""
This example program extracts all command lines and environment variables passed to a program by its PID.

Its output is in JSON format for easy reading.

It uses the KERN_PROCARGS2 sysctl call, which is unique to macOS and uses a rather cumbersome data structure

- int32 (4 bytes) argc
- null terminated string program path, padded with zeroes so it's always stored as a multiple of 8 bytes
- as much null terminated strings as there are cmdline arguments, matching the argc value
- a variable set of null terminated strings containing the environment variables formatted as VARIABLE_NAME=VARIABLE_VALUE

"""
import sys, json
from ctypes import CDLL, create_string_buffer, c_int, c_int32, c_size_t, sizeof, byref, memmove, pointer 

# Loading C library functions through ctypes

libc = CDLL('libc.dylib')

# Defining some magic numbers for the SYSCTL calls, including ARG_MAX as a dependancy

CTL_KERN = 1
KERN_ARGMAX = 8
ARGMAX_ARGCOUNT = 2
KERN_PROCARGS2 = 49
PROCARG2_ARGCOUNT = 3

def get_ARGMAX_c_size_t() -> c_size_t:
    SYSCTL_CALL = ( c_int * ARGMAX_ARGCOUNT )( CTL_KERN, KERN_ARGMAX )
    ARGMAX = c_int()
    result = libc.sysctl(SYSCTL_CALL, ARGMAX_ARGCOUNT, byref(ARGMAX), byref(c_size_t(sizeof(ARGMAX))), None, c_size_t(0))
    return c_size_t(ARGMAX.value)

def progArgsByPid(PID: int) -> dict:
    SYSCTL_CALL = ( c_int * PROCARG2_ARGCOUNT )( CTL_KERN, KERN_PROCARGS2, PID )
    BLOB = create_string_buffer(ARGMAX.value)
    result = libc.sysctl(SYSCTL_CALL, PROCARG2_ARGCOUNT, byref(BLOB), byref(ARGMAX), None, c_size_t(0))
    if result == 0:
        byteArray = BLOB.raw
        argCount = c_int32()
        memmove(pointer(argCount), byteArray, sizeof(argCount))
        idx = str_start = sizeof(argCount)
        procArg2DataStruct = {
            "argc" : argCount.value,
            "argv" : [],
            "env_variables" : []
        }
        #empty result case
        if byteArray[idx] == 0:
            return procArg2DataStruct
        #scanning for program path
        while True:
            if byteArray[idx] == 0:
                procArg2DataStruct['program'] = byteArray[str_start:idx].decode('utf-8')
                offset = 8 - ( len(procArg2DataStruct['program']) % 8 )
                str_start = idx = idx + offset
                break
            idx += 1
        #scanning for argv
        while argCount.value != 0:
            if byteArray[idx] == 0 and byteArray[idx-1] != 0:
                procArg2DataStruct['argv'].append(byteArray[str_start:idx].decode('utf-8'))
                argCount.value -= 1
            elif byteArray[idx] != 0 and byteArray[idx-1] == 0:
                str_start = idx
            idx += 1
        # environment variables
        while idx < len(byteArray):
            if byteArray[idx] == 0 and byteArray[idx-1] == 0:
                break
            elif byteArray[idx] == 0 and byteArray[idx-1] != 0:
                procArg2DataStruct['env_variables'].append(byteArray[str_start:idx].decode('utf-8'))
            elif byteArray[idx] != 0 and byteArray[idx-1] == 0:
                str_start = idx
            idx += 1
        return procArg2DataStruct
    else:
        print('sysctl call failure')

ARGMAX = get_ARGMAX_c_size_t()

def main(argv):
    if len(argv) != 2:
        sys.exit('usage: {0} PID'.format(argv[0]))
    PID = int(argv[1])
    progArgs = progArgsByPid(PID)
    if progArgs:
        print(json.dumps(progArgs, indent=3))

if __name__ == '__main__':
    main(sys.argv)