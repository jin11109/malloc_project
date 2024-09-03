#!/bin/bash
clone_ptmalloc2_dir="ptmalloc2_with_cold_2"
source_ptmalloc2="ptmalloc2_with_cold"

rm -rf $clone_ptmalloc2_dir
mkdir $clone_ptmalloc2_dir
cp $source_ptmalloc2/_my_arena.c $clone_ptmalloc2_dir/_my2_arena.c
cp $source_ptmalloc2/_my_hooks.c $clone_ptmalloc2_dir/_my2_hooks.c
cp $source_ptmalloc2/_my_malloc-stats.c $clone_ptmalloc2_dir/_my2_malloc-stats.c
cp $source_ptmalloc2/_my_malloc.c $clone_ptmalloc2_dir/_my2_malloc.c
cp $source_ptmalloc2/_my_malloc.h $clone_ptmalloc2_dir/_my2_malloc.h
cp $source_ptmalloc2/Makefile $clone_ptmalloc2_dir/Makefile
cp -r $source_ptmalloc2/sysdeps $clone_ptmalloc2_dir/sysdeps

sed -i 's|_my_|_my2_|g' "$clone_ptmalloc2_dir/_my2_arena.c"
sed -i 's|_my_|_my2_|g' "$clone_ptmalloc2_dir/_my2_hooks.c"
sed -i 's|_my_|_my2_|g' "$clone_ptmalloc2_dir/_my2_malloc-stats.c"
sed -i 's|_my_|_my2_|g' "$clone_ptmalloc2_dir/_my2_malloc.c"
sed -i 's|_my_|_my2_|g' "$clone_ptmalloc2_dir/_my2_malloc.h"
sed -i 's|_my_|_my2_|g' "$clone_ptmalloc2_dir/Makefile"
sed -i 's|#define _MY_VERSION_KEY 0b10101|#define _MY_VERSION_KEY 0b01010|g' "$clone_ptmalloc2_dir/_my2_arena.c"
sed -i 's|libptmalloc2_with_cold|libptmalloc2_with_cold_2|g' "$clone_ptmalloc2_dir/Makefile"
sed -i '$ s|#endif|//#endif|g' "$clone_ptmalloc2_dir/_my2_malloc.h"
sed -i 's|#ifndef _MALLOC_H|//#ifndef _MALLOC_H|g' "$clone_ptmalloc2_dir/_my2_malloc.h"