/*
 * Copyright (C) 2004-2021 Intel Corporation.
 * SPDX-License-Identifier: MIT
 */

/*
 *  This file contains an ISA-portable PIN tool for tracing memory accesses.
 */

#include <stdio.h>
#include <time.h>
//#include <stdatomic.h>
#include "pin.H"

FILE* outputfile;
PIN_LOCK lock;
//atomic_int current;
//atomic_int expected;

// Print a memory read record
VOID Output(VOID* addr) 
{
	/*
	atomic_store(&expected, 0);
	atomic_store(&current, 0);
	while (!atomic_compare_exchange_weak(&current, &expected, 1)) {
		atomic_store(&current, 0);
	}
	*/
	struct timespec ts;
	clock_gettime(CLOCK_REALTIME, &ts);
	fprintf(outputfile, "%p %d %ld %ld\n", addr, PIN_GetPid(), ts.tv_sec, ts.tv_nsec); 
	//atomic_store(&current, 0);
	
	
}

// Is called for every instruction and instruments reads and writes
VOID Instruction(INS ins, VOID* v)
{
	PIN_GetLock(&lock, 645);
    // Instruments memory accesses using a predicated call, i.e.
    // the instrumentation is called iff the instruction will actually be executed.
    //
    // On the IA-32 and Intel(R) 64 architectures conditional moves and REP
    // prefixed instructions appear as predicated instructions in Pin.
    UINT32 memOperands = INS_MemoryOperandCount(ins);

    // Iterate over each memory operand of the instruction.
    for (UINT32 memOp = 0; memOp < memOperands; memOp++)
    {
        if (INS_MemoryOperandIsRead(ins, memOp))
        {
            INS_InsertPredicatedCall(ins, IPOINT_BEFORE, (AFUNPTR)Output, IARG_MEMORYOP_EA, memOp,
                                     IARG_END);
        }
        // Note that in some architectures a single memory operand can be
        // both read and written (for instance incl (%eax) on IA-32)
        // In that case we instrument it once for read and once for write.
        if (INS_MemoryOperandIsWritten(ins, memOp))
        {
            INS_InsertPredicatedCall(ins, IPOINT_BEFORE, (AFUNPTR)Output, IARG_MEMORYOP_EA, memOp,
                                     IARG_END);
        }
    }
	PIN_ReleaseLock(&lock);
}

VOID Fini(INT32 code, VOID* v)
{
    //fprintf(outputfile, "#eof\n");
    //fclose(outputfile);
}

/* ===================================================================== */
/* Print Help Message                                                    */
/* ===================================================================== */

INT32 Usage()
{
    PIN_ERROR("This Pintool prints a outputfile of memory addresses\n" + KNOB_BASE::StringKnobSummary() + "\n");
    return -1;
}

/* ===================================================================== */
/* Main                                                                  */
/* ===================================================================== */

int main(int argc, char* argv[])
{
    if (PIN_Init(argc, argv)) return Usage();

    outputfile = fopen("ldst_info.out", "a");
	PIN_InitLock(&lock);

    INS_AddInstrumentFunction(Instruction, 0);
    PIN_AddFiniFunction(Fini, 0);

    // Never returns
    PIN_StartProgram();

    return 0;
}
