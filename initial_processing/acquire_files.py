#
# Registry Decoder
# Copyright (c) 2011 Digital Forensics Solutions, LLC
#
# Contact email:  registrydecoder@digitalforensicssolutions.com
#
# Authors:
# Andrew Case       - andrew@digitalforensicssolutions.com
# Lodovico Marziale - vico@digitalforensicssolutions.com
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or (at
# your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details. 
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307 USA 
#
from errorclasses import *

from guicontroller import *
import registry_sig
import acquirefiles.acquire_files as aqfile
import shutil, sys

import pytsk3

class acquire_files:

    def __init__(self):
        self.singlefilecounter = 0
        self.reg_sig = registry_sig.registry_sig()

    def add_single_file(self, evidence_file, evidence_type, gui_ref):

        # write the info.txt information
        directory = os.path.join(gui_ref.directory, "registryfiles", "singlefiles", "")
        filename = os.path.join(directory,"info.txt")
        fd = open(filename,"a",0750)

        mtime = int(os.path.getmtime(filename))
    
        fd.write("%s,%d,%d\n" % (evidence_file, mtime, self.singlefilecounter))

        fd.close()

        # copy the evidence file into the case directory
        # copy2 copies mac time as well as the file
        filename = os.path.join(directory,"%d" % self.singlefilecounter)

        shutil.copy2(evidence_file,filename)
        
        self.singlefilecounter = self.singlefilecounter + 1
       
    # check if disk image
    def is_mbr(self, filepath):

        ret = False

        fd = open(filepath, "rb")

        fd.seek(446, 0)

        status = fd.read(1)

        if len(status) == 1 and ord(status) in [0x00, 0x80]:
           
            fd.seek(510, 0)
    
            sig = fd.read(2)

            if ord(sig[0]) == 0x55 and ord(sig[1]) == 0xAA:
                ret = True

        return ret

    # checks if given file is a partition image
    def is_disk_image(self, evidence_file):

        return self.is_mbr(evidence_file) or self.is_partition_image(evidence_file)
        
    def is_partition_image(self, evidence_file):

        isimage = 1

        try:
            img = pytsk3.Img_Info(evidence_file)
            pytsk3.FS_Info(img)
        except:
            isimage = 0
            #print "Not a disk image: ", sys.exc_info()[:2]

        return isimage

 
    # tries to determine the file type of 'evidence_file' based on
    # extension 
    def determine_type_ext(self, evidence_file):

        extension = os.path.splitext(evidence_file)[-1].lower()

        if extension in (".img",".dd",".raw"):
            etype = [DD]

        elif extension  == ".db":
            etype = [RDB]
        
        elif self.is_disk_image(evidence_file): 
            etype = [DD]

        else:
            etype = None

        return etype
        
    def determine_type_sig(self, evidence_file):

        fd = open(evidence_file,"rb")

        checkbuffer = fd.read(0x80)

        # check for a registry file
        ret = self.reg_sig.determine_type(checkbuffer)

        if not ret:
            ret = [UNKNOWN]

        return ret                

    # this gathers the evidence from input files for second stange processing
    def acquire_from_file(self, evidence_file, gui_ref):

        evidence_type = self.determine_type_ext(evidence_file)
        
        if not evidence_type:
            evidence_type = self.determine_type_sig(evidence_file)

        if evidence_type[0] == UNKNOWN:
           
            cont = gui_ref.gui.yesNoDialog("Unable to process %s" % evidence_file, "Would you like to skip this file?") 

            if cont:
                evidence_type = -1  
            else:
                gui_ref.gui.msgBox("Unable to process evidence file %s. Exiting." % evidence_file)
                raise RegAcquireError(evidence_file)

        elif evidence_type[0] == DD:
            # pytsk3
            ac = aqfile.acquire_files(gui_ref.directory, gui_ref.gui)
            ac.acquire_files(evidence_file, gui_ref.gui.acquire_current, gui_ref.gui.acquire_backups)

        elif evidence_type[0] == SINGLEFILE:
            self.add_single_file(evidence_file, evidence_type[1], gui_ref)            
            
        # keep a list of RDB files added
        elif evidence_type[0] == RDB:
            fd = open(os.path.join(gui_ref.directory, "rdb-files.txt"), "a+")            
            fd.write(evidence_file)
            fd.close() 


        return evidence_type




