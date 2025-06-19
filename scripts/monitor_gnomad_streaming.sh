#!/bin/bash
# Monitor gnomAD streaming progress

echo "=== gnomAD v4 Streaming Progress ==="
echo "Time: $(date)"
echo

# Check running processes
echo "Running processes:"
ps aux | grep stream_gnomad_v4_afs | grep -v grep | awk '{print $2, $11, $12, $13, $14}'
echo

# Check output files
echo "Output files:"
if [ -d "out/gnomad_v4_afs" ]; then
    ls -lh out/gnomad_v4_afs/*.tsv 2>/dev/null | awk '{print $5, $9}'
fi
echo

# Check latest log entries
echo "Latest progress (common variants):"
if [ -f "out/logs/gnomad_common_variants.log" ]; then
    tail -5 out/logs/gnomad_common_variants.log | grep -E "(Chr|variants processed|complete)"
fi
echo

echo "Latest progress (full genomes):"
if [ -f "out/logs/gnomad_genomes_full.log" ]; then
    tail -5 out/logs/gnomad_genomes_full.log | grep -E "(Chr|variants processed|complete)"
fi
echo

# Estimate completion
if [ -f "out/gnomad_v4_afs/gnomad_v4_genome_afs.tsv" ]; then
    lines=$(wc -l < out/gnomad_v4_afs/gnomad_v4_genome_afs.tsv)
    echo "Full genome variants collected so far: $lines"
    echo "Estimated progress: $(( lines * 100 / 600000000 ))%"
fi

echo
echo "To stop streaming: kill <PID>"
echo "To view full logs: tail -f out/logs/gnomad_*.log"