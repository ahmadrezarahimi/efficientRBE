#!/bin/sh

# delete old data files if they are present
rm *.db

# check if existing benchmarks will be overwritten
rm -i *.csv
outfile="bench.txt"
if [ -f $outfile ]; then
    rm -i $outfile
fi

echo "curve: BLS12-381" >> $outfile
echo "" >> $outfile

echo "===================" >> $outfile
echo " base construction " >> $outfile
echo "===================" >> $outfile
# run benchmarks for 10K...10M
for N in  10000 100000 1000000 10000000
do
    echo "base N=$N"
    echo "***** N=$N *****" >> $outfile

    # times
    (python3 bench.py -N $N) >>$outfile
    echo "" >> $outfile

    # sizes
    echo "Param Sizes (bytes) -- for one full block" >> $outfile
    echo "--------------------------" >> $outfile
    crssize=$(ls -la crs.db | awk -F " " {'print $5'})
    echo "crs.db:\t\t$crssize" >> $outfile
    echo "" >> $outfile

    rm *.db
done

echo "===================" >> $outfile
echo " efficient updates " >> $outfile
echo "===================" >> $outfile
# run benchmarks for 10K...100M
for N in  10000 100000 1000000 10000000 #100000000
do
    echo "efficient N=$N"
    echo "" >> $outfile
    echo "***** N=$N *****" >> $outfile

    # times
    (python3 bench.py -N $N -e) >>$outfile
    echo "" >> $outfile

    # sizes
    echo "Param Sizes (bytes) -- for one full block" >> $outfile
    echo "--------------------------" >> $outfile
    crssize=$(ls -la crs.db | awk -F " " {'print $5'})
    echo "crs.db:\t\t$crssize" >> $outfile
    echo "" >> $outfile

    rm *.db
done
