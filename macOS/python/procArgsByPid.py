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
from os import sysconf
from ctypes import CDLL, create_string_buffer, c_int, c_int32, c_size_t, sizeof, byref, memmove, pointer 

# Loading C library functions through ctypes

libc = CDLL('libc.dylib')

# Defining some magic numbers for the SYSCTL call, retrieving the current system ARG_MAX size

CTL_KERN = 1
KERN_PROCARGS2 = 49
ARG_MAX = sysconf('SC_ARG_MAX')

def progArgsByPid(PID):
    PROCARG2_SYSCTL_DEF = ( CTL_KERN, KERN_PROCARGS2, PID )
    dataBlob = create_string_buffer(ARG_MAX)
    sysctlCallDef = c_int * len(PROCARG2_SYSCTL_DEF)
    sysctlCall = sysctlCallDef()
    for i, v in enumerate(PROCARG2_SYSCTL_DEF):
        sysctlCall[i] = c_int(v)
    dataBlobSize = c_size_t(sizeof(dataBlob))
    result = libc.sysctl(sysctlCall, len(PROCARG2_SYSCTL_DEF), byref(dataBlob), byref(dataBlobSize), None, c_size_t(0))
    if result == 0:
        rawData = dataBlob.raw
        aBytes = bytes(rawData)
        argCount = c_int32()
        memmove(pointer(argCount), aBytes, sizeof(argCount))
        idx = str_start = sizeof(argCount)
        procArg2DataStruct = {
            "argc" : argCount.value,
            "argv" : [],
            "env_variables" : []
        }
        #scanning for program path
        while True:
            if rawData[idx] == 0:
                procArg2DataStruct['program'] = rawData[str_start:idx].decode('utf-8')
                offset = 8 - ( len(procArg2DataStruct['program']) % 8 )
                str_start = idx + offset + 1
                idx += 1
                break
            idx += 1
        #scanning for argv
        while argCount.value != 0:
            if rawData[idx] == 0 and rawData[idx-1] != 0:
                procArg2DataStruct['argv'].append(rawData[str_start:idx].decode('utf-8'))
                argCount.value -= 1
            if rawData[idx] != 0 and rawData[idx-1] == 0:
                str_start = idx
            idx += 1
        # environment variables
        while True:
            if rawData[idx] == 0 and rawData[idx-1] == 0:
                break
            if rawData[idx] == 0 and rawData[idx-1] != 0:
                procArg2DataStruct['env_variables'].append(rawData[str_start:idx].decode('utf-8'))
            if rawData[idx] != 0 and rawData[idx-1] == 0:
                str_start = idx
            idx += 1
        return procArg2DataStruct
    else:
        print('sysctl call failure')

def main(argv):
    if len(argv) != 2:
        sys.exit('usage: {0} PID'.format(argv[0]))
    PID = int(argv[1])
    progArgs = progArgsByPid(PID)
    if progArgs:
        print(json.dumps(progArgs, indent=3))

if __name__ == '__main__':
    main(sys.argv)