#!/usr/bin/env python

"""

****************
filespec
****************

License
**************

   filespec.py (c) 2014 Certified Scientific Software 

   This file is distributed as free software: you can redistribute it and/or modify
   it freely.

   It is distributed in the hope that it will be useful,
   but WITHOUT ANY WARRANTY; without even the implied warranty of
   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  

Description
****************
   This module offers an interface to files with data in the spec 
   file format. The format specificiation can be consulted online at the _`certif.com`
   website.

   A spec file normally consists of a series of header blocks and scan blocks. 
   Data comes after scan blocks. Sometimes comment lines can be also be found in between blocks. 
   These comment lines could contain for example the result of user calculations after a scan, 
   or pure comments.  For practical purposes comment lines will be considered to belong to the 
   preceding scan or header block.

.. _`certif.com`: http://www.certif.com/spec_help/scans.html

"""


import re
import numpy
import os
import sys
import time

try:
    from SPlotLogger import dprint
except ImportError:
    dprint = str

class FileSpec(list):
   """
   FileSpec class documentation
   """

   def __init__(self, filename):

       list.__init__(self)

       self.filename = filename
       self.origfilename = None
       self.headers  = []
       self.lastpos  = 0

       self.inheader = False

       self.filestat = os.stat(self.filename)
       self.st_size  = 0

       self.scans    = {}     #  dictionary to hold references (by scan number) to the scanlist

       self._indexscans()

   def absolutePath(self):
       return os.path.abspath(self.filename)

   def update(self):

       currstat = os.stat(self.filename)

       if currstat.st_size > self.st_size:
          self.st_size = currstat.st_size
          self._indexscans()
          modified = True
       else:
          modified = False

       return modified

   def getScanByNumber(self, scanno, scanorder=0):
       if scanno in self.scans: 
            if scanorder >= 0 and scanorder < len( self.scans[scanno] ) :
                 scan = self.scans[scanno][scanorder]
                 return scan
       else:
            return None

   def getTimeCreated(self):
       if self.headers:
           return self.headers[0].getDate()

   def getUser(self):
       if self.headers:
           return self.headers[0].getUser()

   def getSpec(self):
       if self.headers:
           return self.headers[0].getSpec()

   def getTimeModified(self):
       if not self.filename:
            return None

       mtime = os.stat(self.filename).st_mtime
       return time.asctime( time.localtime( mtime ))

   def getNumberScans(self):
       return len(self)

   def getNumberHeaders(self):
       return len(self.headers)

   def getInfo(self):
       """Returns user and application"""
       ctime = self.getTimeCreated()
       mtime = self.getTimeModified()
       user = self.getUser()
       spec = self.getSpec()
       return [ctime,mtime,user,spec]

   def _indexscans(self):

       self.fd  = open(self.filename, "rb")

       if len(self) > 0:
           fb = self[-1]
           self.fd.seek( self.lastpos )
       else:
           fb = None

       line = self.fd.readline()
       lineno = -1

       while line:
           lineno += 1
           sline = line.strip()

           if len(sline) >= 2 and sline[0] == "#" and sline[1] in ['S','F','E']:

               btype      = sline[1]
               blockstart = self.lastpos
               blockline = lineno 

               if fb: fb.end()

               if btype == 'F':
                   self.origfilename = sline[2:].strip()
                   fb = Header(blockstart, blockline)
                   self.inheader = True
                   self.headers.append(fb)
               elif btype == 'E' and not self.inheader:
                   fb = Header(blockstart, blockline)
                   self.inheader = True
                   self.headers.append(fb)
               elif sline[1] == 'S':
                   fb = Scan(blockstart, blockline)
                   self.inheader = False
                   self.append(fb)
                   fb._setScanIndex( len(self) )
                   if len(self.headers): 
                       fb._setFileHeader( self.headers[-1] )  #  Assign last added header to current scan

               if self.origfilename:
                   fb.setFileName( self.origfilename )

           if sline:
               fb.addLine(sline)

           self.lastpos = self.fd.tell()

           line = self.fd.readline()

       # register last block
       fb.end()

       # correct the scan order if necessary 
       # assign number in file

       self.scans = {}
       scanidx = 0

       for scan in self:
          scanno = scan.getNumber()
          if scanno not in self.scans:
             self.scans[scanno] = []

          self.scans[scanno].append( scan )
          scan._setOrder( len(self.scans[scanno]) - 1 )
          scan._setNumberInFile(scanidx)
          scanidx += 1

       self.fd.close()

class FileBlock:

    respecuser = re.compile("(?P<spec>.*?)\s+User\s+=\s+(?P<user>.*?)$")

    def __init__(self, start, firstline):

        self.start  = start
        self.firstline  = firstline
        self.lines  = []
        self._filename = None
        self._contains_error = False
        self._error_messages = []
        self._id = ""

        self.funcs = {
            'S': self.addSLine,
            'E': self.addEpochLine,
            'F': self.addFileLine,
            'D': self.addDateLine,
            'N': self.addColumnsLine,
            'L': self.addLabelLine,
            'O': self.addMotorLabelLine,
            'o': self.addMotorMneLine,
            'J': self.addCounterLabelLine,
            'j': self.addCounterMneLine,
            'U': self.addUserLine,
            'C': self.addCommentLine,
            'P': self.addMotorPositionLine,
            'T': self.addTimeLine,
            'G': self.addGeoLine,
            'Q': self.addQLine,
            '@': self.addExtraLine,
        }

        self.resetParsedData()

    def resetParsedData(self):
        # Default
        self.is_parsed = False

        self._data  = []
        self._mcas  = []

        self._number = 0
        self._command = ""
        self._count_time = 0
        self._filename = ""
        self._epoch = 0
        self._date = ""
        self._columns = 0
        self._labels = None
        self._motor_labels =  []
        self._motor_mnes =  []
        self._counter_labels = []
        self._counter_mnes = []
        self._motor_positions = []
        self._comment_lines = []
        self._user_lines = []
        self._geo_pars = []
        self._qvalue = 0
        self._extra_lines = []
        self._wrong_lines = []
        self._error_messages = []
        self._contains_error = False

        self.reading_mca = False

    def addLine(self, line):
        self.lines.append(line)

    def end(self):
        pass

    def parse(self):

        lineno = -1

        for sline in self.lines:
            lineno += 1
            if not sline:
                continue

            if len(sline) > 1 and sline[0] == "#":
                  widx = sline.find(" ")
                  if widx < 2:
                     continue  
            
                  metakey = sline[1]
                  metaval = sline[2:widx].strip()
                  content = sline[widx:].strip()

                  if metakey in self.funcs:
                      self.funcs[metakey]( content.strip(), metaval )
                  else:
                      self.wrongLine(lineno, sline, "unknown header line (%s) " % metakey )
            else:
                # TODO:  handle MCA blocks
                # for now we work only with normal data lines

                if sline[0:2] == '@A':
                    sline = sline[2:]
                    self.reading_mca = True
                    self.tmpmca = McaData()

                if self.reading_mca:
                    complete = self.tmpmca._addLine( sline ) 
                    if complete:
                        self._mcas.append( self.tmpmca )
                        self.reading_mca = False
                else:
                    try:
                        try:
                            dataline = map(float, sline.strip().split())
                        except:
                            self.wrongLine(lineno, sline, "wrong data line" )
                            continue

                        if len(dataline) != self._columns:
                            self.wrongLine(lineno, sline, "wrong number of columns" )
                        else:
                            self._data.append( dataline )
                    except ValueError:
                        self.wrongLine(lineno, sline, "cannot parse line " )

        self.is_parsed = True
        self.finalizeParsing()

    def finalizeParsing(self):
        pass

    def wrongLine(self, lineno, sline, errmsg):
        self._wrong_lines.append( [errmsg, sline] )
        line = "%s (%s)" % (lineno+1, self.firstline+lineno+1)
        ermsg = "erroneous data / %s " % errmsg
        self._error_messages.append( [self._id, line, ermsg] )
        self._contains_error = True

    def setFileName(self, filename):
        self._filename = filename

    def addSLine(self, content, keyval=None ):
        # Scan line is scannumber and command
        vals = content.split()  
        self._number  = int(vals[0])
        self._id = self._number
        self._command = " ".join( vals[1:] )

    def addFileLine(self,content, keyval=None):
        self._filename = content

    def addEpochLine(self,content, keyval=None):
        self._epoch    = int(content)

    def addDateLine(self,content, keyval=None):
        self._date    = content

    def addColumnsLine(self,content, keyval=None):
        if not self._columns:
            self._columns = int(content)
        else:
            pass

    def addLabelLine(self,content, keyval=None):
        if self._labels is None:
            self._labels = re.split("\s\s+",content)
        else:
            pass

    def addMotorLabelLine(self,content, keyval=None):
        # Beware of double spacing
        self._motor_labels.extend( re.split("\s\s+", content) )

    def addMotorMneLine(self,content, keyval=None):
        self._motor_mnes.extend( re.split("\s", content) )

    def addCounterLabelLine(self,content, keyval=None):
        # Beware of double spacing
        self._counter_labels.extend( re.split("\s\s+", content) )

    def addCounterMneLine(self,content, keyval=None):
        # Beware of double spacing
        self._counter_mnes.extend( re.split("\s", content) )

    def addMotorPositionLine(self,content, keyval=None):
        self._motor_positions.extend(content.split(" "))

    def addUserLine(self,content, keyval=None):
        self._user_lines.append( content )

    def addCommentLine(self,content, keyval=None):
        self._comment_lines.append( content )

    def addTimeLine(self,content, keyval=None):
        parts = content.split()
        if len(parts) > 1:
            units = re.sub("[\)\(]", "", parts[1])
            self._count_time = [parts[0], units]
        else:
            self._count_time = [content, ""]

    def addGeoLine(self,content, keyval=None):
        self._geo_pars.append( content.split() )

    def addQLine(self,content, keyval=None):
        self._qvalue = content

    def addExtraLine(self,content, keyval=None):
        self._extra_lines.append( [keyval, content] )
   
    def getDate(self):
        """
        Returns the date when the scan was started
        """
        if not self.is_parsed:
           self.parse()
        return self._date

    def getUserSpec(self):

        comments = self._comment_lines

        if comments:
           for line in comments:
              mat = self.respecuser.search( line )
              if mat:
                 return [ mat.group("user"), mat.group("spec") ]

        return "" 

    def getSpec(self):
        """
        Returns the name of the spec application from which the file was created
        """
        if not self.is_parsed:
           self.parse()

        return self.getUserSpec()[1]

    def getUser(self):
        """
        Returns the name of the unix user that created the file 
        """
        if not self.is_parsed:
           self.parse()

        return self.getUserSpec()[0]


class Header(FileBlock):
    """ 
    Class representing a file header.
    """
    def __init__(self, start, firstline):
        FileBlock.__init__(self, start, firstline)

    def end(self):
        self.parse()

class Scan(FileBlock):
    """
    Scan class documentation
    """

    def __init__(self, start, firstline):
        FileBlock.__init__(self, start, firstline)
        self._fileheader = None
        self._numberinfile = -1
        self._order      = 1

    def end(self):
        self.resetParsedData()

    def finalizeParsing(self):

        # prepare motor positions
        labels = self.getMotorNames()
        poss   = self._motor_positions
        poserr = False
        self.motor_positions_list = None
        
        if not labels:
            ermsg = "no motor names"
            self._error_messages.append( [self._id, "", ermsg] )
            self._contains_error = True
            poserr = True

        elif len(labels) != len(poss):
            ermsg = "number of motor labels and positions are different" 
            self._error_messages.append( [self._id, "", ermsg] )
            self._contains_error = True
            poserr = True

        if not poserr:
            self.motor_positions_list = zip( labels, poss )

    def _setFileHeader(self, header):
        self._fileheader = header
 
    def _setScanIndex(self, idx):
        self._index = idx

    def getScanIndex(self):
        """
        Returns the position of the scan in the file
        """
        return self._index

    def getNumber(self):
        """ 
        Returns scan number as it appeared in spec. 
        Remember that it could be that more than one scan in the file will have the same number. 
        The scan index is the position of the scan in the file. The scan number is the number given by spec
        to the scan at the time it was executed.  
        """
        if not self.is_parsed:
           self.parse()
        return self._number

    def getOrder(self):
        """ 
        Returns scan order for the scan. The combination of scan number/scan order should be unique for a scan.
        in a file.  The first scan with a certain number in the file will have order 1.  If another scan in the file
        uses the same number, it will be associated with order 2 and so on.
        """
        return self._order
        
    def _setNumberInFile(self, number):
        self._numberinfile = number

    def getNumberInFile(self):
        return self._numberinfile

    def getLines(self):
        """
        Returns number of data lines
        """
        return len(self._data)

    def getColumns(self):
        """
        Returns number of columns from scan header
        """
        if not self.is_parsed:
           self.parse()
        return self._columns

    def getLabels(self):
        """
        Returns the labels for the data columns 
        """
        if not self.is_parsed:
           self.parse()
        return self._labels
        
    def getCommand(self):
        """
        Returns a string containing the command that was run in spec to start the scan
        """
        if not self.is_parsed:
           self.parse()
        return self._command
        
    def getMotorNames(self):
        """
        Returns a list with motor names
        """
        if not self.is_parsed:
           self.parse()

        if self._motor_labels:
            return self._motor_labels
        elif self._fileheader and self._fileheader._motor_labels:
            return self._fileheader._motor_labels
        else:
            return None

    def getMotorMnemonics(self):
        """
        Returns a list with motor mnemonics. Motor mnemonics are saved in files only since spec version 6.0.10
        """
        if not self.is_parsed:
           self.parse()

        if self._motor_mnes:
            return self._motor_mnes
        elif self._fileheader and self._fileheader._motor_mnes:
            return self._fileheader._motor_mnes
        else:
            return None

    def getCounterNames(self):
        """
        Returns a list with counter names. Counter names are saved in files only since spec version 6.0.10
        """
        if not self.is_parsed:
           self.parse()

        if self._counter_labels:
            return self._counter_labels
        elif self._fileheader and self._fileheader._counter_labels:
            return self._fileheader._counter_labels
        else:
            return None

    def getCounterMnemonics(self):
        """
        Returns a list with counter mnemonics. Counter mnemonics are saved in files only since spec version 6.0.10
        """
        if not self.is_parsed:
           self.parse()

        if self._counter_mnes:
            return self._counter_mnes
        elif self._fileheader and self._fileheader._counter_mnes:
            return self._fileheader._counter_mnes
        else:
            return None

    def getMotorPositions(self):
        """
        Returns a dictionary with motor names and positions. These are the positions of the motors when the scan was started
        """
        if not self.is_parsed:
           self.parse()

        return self.motor_positions_list

    def getUser(self):
        if self._fileheader:
            return self._fileheader.getUser()

    def getSpec(self):
        if self._fileheader:
            return self._fileheader.getSpec()
        

    def getDate(self):
        """
        Returns the date when the scan was started
        """
        if not self.is_parsed:
           self.parse()
        return self._date

    def getFileDate(self):
        """
        Returns the date when the file was created
        """
        if self._fileheader:
           return self._fileheader._date
        else: 
           return None

    def getSource(self):
        """
        Returns the path of the file as it appears in the file header
        """
        if self._fileheader:
           if self._fileheader._filename:
               return self._fileheader._filename
        
        return ""

    def getGeometry(self):
        """
        Returns geometry values as saved in the file.  Check the spec documentation for the meaning of these values
        """
        if not self.is_parsed:
           self.parse()
        return [' '.join(line) for line in self._geo_pars]

    def getHKL(self):
        """
        Returns a list with HKL values at the beginning of the scan
        """
        if not self.is_parsed:
           self.parse()
        return self._qvalue

    def getFileEpoch(self):
        """
        Returns the epoch of the file creation. It is possible to find the absolute epoch for any scan time by adding
        the file epoch with the value in the Epoch column of the scan
        """
        if self._fileheader:
            return self._fileheader._epoch
        else:
            return None

    def getCountTime(self):
        """
        Returns a list with two values: counting time and units
        if time units cannot be found in file the units value is left empty
        """
        if not self.is_parsed:
            self.parse()
        return self._count_time

    def getComments(self):
        """
        Returns comments in the scan. Aborted termination can be found in this way
        """
        if not self.is_parsed:
            self.parse()
        return self._comment_lines
        
    def getUserLines(self):
        if not self.is_parsed:
            self.parse()
        return self._user_lines

    def getExtra(self):
        """
        Returns extra lines starting with "@" character. These are normally lines related with MCA data
        """
        if not self.is_parsed:
            self.parse()
        return self.getExtraLines()

    def getExtraLines(self):
        if not self.is_parsed:
            self.parse()
        return [' '.join(line) for line in self._extra_lines]
        
    def getMeta(self):
        """ 
        Returns a dictionary with the most relevant metdata information
        """ 
        if not self.is_parsed:
            self.parse()

        meta = {
            'spec':   "",
            'user':   "",
            'source': "",
            'HKL':    "",
            'date':   "",
            'scanno': "",
            'motors': None,
            'comments': None,
            'errors': None,
        }

        # spec and user. In fileheader comment line
        meta["spec"] = self.getSpec()
        meta["user"] = self.getUser()
        meta["source"] = self.getSource()
        meta["HKL"] = self.getHKL()
        meta["date"] = self.getDate()
        meta["scanno"] = self.getNumber()
        meta["motors"] = self.getMotorPositions()
        meta["motnames"] = self.getMotorNames()
        meta["comments"] = self.getComments()
        meta["order"]= self.getOrder()
        meta["noinfile"] = self.getNumberInFile()
        meta["points"] = self.getLines()
        meta["columns"] = self.getColumns()
        meta["userlines"] = self.getUserLines()
        meta["geo"] = self.getGeometry()
        meta["extra"] = self.getExtra()

        motmnes = self.getMotorMnemonics()
        if motmnes:
            meta["motmnes"]   = self.getMotorMnemonics()
             
        if self._contains_error:
            meta['errors'] = self._error_messages

        return meta

    def getData(self):
        """ 
        Returns a numpy array with all data in the scan
        """ 
        if not self.is_parsed:
           self.parse()

        if self._data:
            return numpy.array( self._data, dtype=numpy.float )
        else:
            return numpy.empty((0,self._columns))


    def getNumberMcas(self):
        """ 
        Returns the number of mcas in the file
        """ 
        if not self.is_parsed:
           self.parse()
        return len( self._mcas )

    def getMcas(self):
        """ 
        Returns a list of 1D numpy arrays in the scan, each of them being a spectrum from a 1D detector
        """ 
        if not self.is_parsed:
           self.parse()
        return [ self._mcas[idx] for idx in range(len(self._mcas)) ]

    def getMcaData(self, index):
        """ 
        Returns the data for spectrum with index "index" in the scan.
        """ 
        if not self.is_parsed:
           self.parse()
        if index < len(self._mcas):
           return self._mcas[index].getData()

    def _setOrder(self, order):
        self._order = order

    def __str__(self):
        if not self.is_parsed:
           self.parse()
        if self._order > 1:
            return "%s.%s %s" % (self._number, self._order, self._command )
        else:
            return "%s %s" % (self._number, self._command )

    def save(self, outfile, format="spec", append=False, columns=None, mcas=False):
        """ scan.save method produces a simple output meant to export scan data to 
format readable by excel and other programs
"""
   
        data = self.getData()
        meta = {}

        meta['command'] = self.getCommand()
        meta['number'] = self.getNumber()
        meta['columns'] = data.shape[1]

        dprint("saving scan (format=%s) to file %s" % (format, outfile) )

        if append:
           ofd = open(outfile,"a") 
        else: 
           ofd = open(outfile,"w") 

        if format == "tabs":
           labsep = "\t"
           datsep = "\t"
           first = ""
        elif format == "csv":
           labsep = ","
           datsep = ","
           first = ""
        elif format == "spec":
           labsep = "  "
           datsep = " "
           first = """
#S %(number)s %(command)s
#N %(columns)s
#L """ % meta
          

        ofd.write( first + labsep.join( self.getLabels()) + "\n")
        for row in range(data.shape[0]):
           outline = datsep.join( ["%.12g"%val for val in data[row] ]) + "\n"
           ofd.write(outline)
        ofd.write("\n")

class McaData:
     """ 
     The class MCA data represents 1D data
     """
     def __init__(self): 
         self.data  = []
         self.calib = None

     def getCalib(self):
         return self.calib

     def setCalib(self, calib):
         self.calib = calib

     def getData(self):
         channels = range(len(mcadata))
         if self.data:
             return numpy.array( [channels, self.data], dtype=numpy.float ).transpose()
         else:
             return numpy.empty((0,1))

     def _addLine(self, line):
         if line.strip()[-1] ==  "\\":
            dataline = line.strip()[:-1]
            complete = False
         else:
            dataline = line
            complete = True

         self.data.extend( map(float, dataline.split() ))
         return complete

