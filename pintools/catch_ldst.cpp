/*
 * Copyright (C) 2004-2021 Intel Corporation.
 * SPDX-License-Identifier: MIT
 */

/*
 *  This file contains an ISA-portable PIN tool for tracing memory accesses.
 */

#include <stdio.h>
#include <time.h>

#include "pin.H"

FILE* outputfile;
PIN_LOCK lock;

// Print a memory read record
VOID Output_read(VOID* addr, int size) {
    //fprintf(outputfile, "%d %p %d r\n", PIN_GetPid(), addr, size);
    char output[128];
    sprintf(output, "%d %p %d r\n", PIN_GetPid(), addr, size);
    //printf("test %s\n", output);
    fwrite(output, sizeof(output), 1, outputfile);
}
// Print a memory write record
VOID Output_write(VOID* addr, int size) {
    char output[128];
    sprintf(output, "%d %p %d w\n", PIN_GetPid(), addr, size);
    fwrite(output, sizeof(output), 1, outputfile);
}

// Is called for every instruction and instruments reads and writes
VOID Instruction(INS ins, VOID* v) {
    PIN_GetLock(&lock, 645);
    // True if this instruction reads memory
    if (INS_IsMemoryRead(ins) && INS_IsStandardMemop(ins)) {
        INS_InsertPredicatedCall(ins, IPOINT_BEFORE, (AFUNPTR)Output_read,
                                 IARG_MEMORYREAD_EA, IARG_MEMORYREAD_SIZE,
                                 IARG_END);
    }
    // True if this instruction has 2 memory read operands
    if (INS_HasMemoryRead2(ins) && INS_IsStandardMemop(ins)) {
        INS_InsertPredicatedCall(ins, IPOINT_BEFORE, (AFUNPTR)Output_read,
                                 IARG_MEMORYREAD2_EA, IARG_MEMORYREAD_SIZE,
                                 IARG_END);
    }
    // True if this instruction writes memory
    if (INS_IsMemoryWrite(ins) && INS_IsStandardMemop(ins)) {
        INS_InsertPredicatedCall(ins, IPOINT_BEFORE, (AFUNPTR)Output_write,
                                 IARG_MEMORYWRITE_EA, IARG_MEMORYWRITE_SIZE,
                                 IARG_END);
    }

    PIN_ReleaseLock(&lock);
}

VOID Fini(INT32 code, VOID* v) {
    // fprintf(outputfile, "#eof\n");
    fclose(outputfile);
}

/* ===================================================================== */
/* Print Help Message                                                    */
/* ===================================================================== */

INT32 Usage() {
    PIN_ERROR("This Pintool prints a outputfile of memory addresses\n" +
              KNOB_BASE::StringKnobSummary() + "\n");
    return -1;
}

/* ===================================================================== */
/* Main                                                                  */
/* ===================================================================== */

int main(int argc, char* argv[]) {
    if (PIN_Init(argc, argv)) return Usage();

    outputfile = fopen("./fifo_pintools", "a");
    PIN_InitLock(&lock);

    INS_AddInstrumentFunction(Instruction, 0);
    PIN_AddFiniFunction(Fini, 0);

    // clock_gettime(CLOCK_REALTIME, &init_ts);

    // Never returns
    PIN_StartProgram();

    return 0;
}
