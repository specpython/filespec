..  %W%  %G% CSS
..
..  "splot" Release %R%
..
..  Copyright (c) 2013,2014,2015,2016
..  by Certified Scientific Software.
..  All rights reserved.
..
..  Permission is hereby granted, free of charge, to any person obtaining a
..  copy of this software ("splot") and associated documentation files (the
..  "Software"), to deal in the Software without restriction, including
..  without limitation the rights to use, copy, modify, merge, publish,
..  distribute, sublicense, and/or sell copies of the Software, and to
..  permit persons to whom the Software is furnished to do so, subject to
..  the following conditions:
..
..  The above copyright notice and this permission notice shall be included
..  in all copies or substantial portions of the Software.
..
..  Neither the name of the copyright holder nor the names of its contributors
..  may be used to endorse or promote products derived from this software
..  without specific prior written permission.
..
..     * The software is provided "as is", without warranty of any   *
..     * kind, express or implied, including but not limited to the  *
..     * warranties of merchantability, fitness for a particular     *
..     * purpose and noninfringement.  In no event shall the authors *
..     * or copyright holders be liable for any claim, damages or    *
..     * other liability, whether in an action of contract, tort     *
..     * or otherwise, arising from, out of or in connection with    *
..     * the software or the use of other dealings in the software.  *

SPEC data file format
+++++++++++++++++++++

SPEC data files are ASCII text files.  One data file contains several datasets organized
sequencially in the file.

Header blocks and data blocks alternate in the file. Two types of header blocks can be found
in a file.  File header give general information affecting all the scans in the file. This includes
user name, geometry of the SPEC application creating the file or motor names, for example.
Scan header blocks list information about the following data block.

Sequence
-------------
In a simple file the sequence of blocks should be something like
   <FileBlock> - <ScanBlock1> - <DataBlock1> - <ScanBlock2> - <DataBlock2> ....

Headers
+++++++

The following are recognized header keys:

'S' - Scan

'E' - Epoch

'F' - File

'D' - Date 

'N' - Columns 

'L' - Labels 

'O' - Motor Labels 

'o' - Motor Mnemonics 

'J' - Counter Labels 

'j' - Counter mnemonics 

'U' - User defined 

'C' - Comment

'P' - Motor Positions

'T' - Time

'G' - Geometry

'Q' - Q line

'@' - Extra line
   @MCA     #  example #@MCA 16C  --  16 columns
   @CHANN   #  example #@CHANN 8192 0 8191 1   -- 8192 total channels saving from 0 to 8191
   @CTIME   #  example #@CTIME 10 9.8 10  --  <programmed> <live> <real>
   @CALIB   #  example #@CALIB  1 3.5 0.2  -- A,B,C values of channel-energy calibration
   @MCA_NB  #  example #@MCA_NB 2 -- two 1D detectors in every scan point (or in total)
   @DET_%detno%  # example #@DET_0 Mythen1 -- Name of first detector
   @ROI # example #@ROI Roi1 80 230 0 -- Roi name (must match counter name) start end det-no

Data
++++

Data lines contains just numbers from the first character. Each value is separated with one or more spaces.

For 1D detectors and MCAs, each data value is a 1D dimensional array.

