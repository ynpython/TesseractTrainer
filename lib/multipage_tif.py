"""
API alloiwing the user to generate "black on white" multipage tif images using a specified text, font and font-size,
and to generate "box-files": a file containing a list of characters and their associated box coordinates
and page number.
"""

import Image
import ImageFont
import ImageDraw
import glob
import subprocess

from os import system
 

class MultiPageTif(object):
    """ A class allowing generation of a multi-page tif """

    def __init__(self, text, W, H, start_x, start_y, font_name, font_path, fontsize, exp_number, dictionary_name):
        self.W = W
        self.H = H
        self.start_x = start_x
        self.start_y = start_y
        self.text = text.split(' ')
        self.font = ImageFont.truetype(font_path, fontsize)
        self.font_name = font_name
        self.dictionary_name = dictionary_name
        self.prefix = ".".join([dictionary_name, font_name, "exp"+str(exp_number)])
        self.boxlines = []
        self.indiv_page_prefix = 'page'

    def generate_tif(self):
        """ Create several individual tifs from text and merge them 
        into a multi-page tif, and finally delete all individual tifs
        """
        self._fill_pages()
        self._multipage_tif()
        self._clean()

    def generate_boxfile(self):
        """ Generate a boxfile from the multipage tif. 
        The boxfile will be named {self.prefix}.box
        """
        boxfile_path = self.prefix + '.box'
        print "Generating boxfile %s" %(boxfile_path)
        with open(boxfile_path, 'w') as boxfile:
            for boxline in self.boxlines:
                boxfile.write(boxline + '\n')

    def _new_tif(self, color="white"):
        """ Create and returns a new RGB blank tif """
        return Image.new("RGB", (self.W, self.H), color=color)

    def _save_tif(self, tif, page_number):
        """ Save the argument tif using 'page_number' argument in filename.
        The filepath will be {self.indiv_page_prefix}{self.page_number}.tif
        """
        tif.save(self.indiv_page_prefix +  str(page_number) + '.tif')
    
    def _fill_pages(self):
        """ Fill individual tifs with text, and save them to disk.
        Each time a character is written in the tif, its coordinates will be added to the self.boxlines
        list (with the exception of white spaces).
        
        All along the process, we manage to contain the text within the image limits
        """
        tif = self._new_tif()
        draw = ImageDraw.Draw(tif)
        page_nb = 0
        x_pos = self.start_x
        y_pos = self.start_y
        print 'Generating individual tif image %s' %(self.indiv_page_prefix +  str(page_nb) + '.tif')
        for word in self.text:
            word += ' '  # add a space between each word 
            wordsize_w, wordsize_h = self.font.getsize(word)
            # Check if word can fit the line, if not, newline
            # if newline, check if the newline fits the page
            # if not, save the current page and create a new one
            if not word_fits_in_line(self.W, x_pos, wordsize_w):
                if newline_fits_in_page(self.H, y_pos, wordsize_h):
                    # newline
                    x_pos = self.start_x
                    y_pos += wordsize_h
                else:
                    # newline AND newpage
                    x_pos = self.start_x
                    y_pos = self.start_y
                    self._save_tif(tif, page_nb)
                    page_nb += 1
                    print 'Generating individual tif image %s' %(self.indiv_page_prefix +  str(page_nb) + '.tif')
                    tif = self._new_tif()
                    draw = ImageDraw.Draw(tif)
            # write word
            for char in word:
                char_w, char_h = self.font.getsize(char)
                char_x0, char_y0 = x_pos, y_pos
                char_x1, char_y1 = x_pos + char_w, y_pos + char_h
                draw.text((x_pos,y_pos), char, fill="black", font=self.font)
                if char != ' ':
                    self._write_boxline(char, char_x0, char_y0, char_x1, char_y1, page_nb)                  
                x_pos += char_w
        self._save_tif(tif, page_nb)

    def _write_boxline(self, char, char_x0, char_y0, char_x1, char_y1, page_nb):
        """ Generate a boxfile line given a character coordinates, and append it to the
        self.boxlines list
        """
        # draw.rectangle([(char_x0, char_y0),(char_x1, char_y1)], outline="red")
        tess_char_x0, tess_char_y0 = pil_coord_to_tesseract(char_x0, char_y0, self.H)
        tess_char_x1, tess_char_y1 = pil_coord_to_tesseract(char_x1, char_y1, self.H)
        boxline = '%s %d %d %d %d %d' % (char, tess_char_x0, tess_char_y0, tess_char_x1, tess_char_y1, page_nb)
        self.boxlines.append(boxline)

    def _multipage_tif(self):
        """ Generate a multipage tif from all the generated tifs.
        The multipage tif will be named #self.prefix}.tif
        """
        tiffcp = ["tiffcp"]
        tifs = glob.glob(self.indiv_page_prefix + '*.tif')
        tifs.sort()
        tiffcp.extend(tifs)
        multitif_name = self.prefix + '.tif'
        tiffcp.append(multitif_name)
        print 'Generating multipage-tif %s' % (multitif_name)
        subprocess.call(tiffcp)
        
    def _clean(self):
        """ Remove all generated individual tifs """
        print "Removing all individual tif images"
        rmtif = 'rm %s*' %(self.indiv_page_prefix)
        system(rmtif)

# Utility functions
def word_fits_in_line(pagewidth, x_pos, wordsize_w):
    """ Return True if a word can fit into a line """
    return (pagewidth - x_pos - wordsize_w) > 0

def newline_fits_in_page(pageheight, y_pos, wordsize_h):
    """ Return True if a new line can be contained in a page """
    return (pageheight - y_pos - (2 * wordsize_h)) > 0

def pil_coord_to_tesseract(pil_x, pil_y, tif_h):
    """ 
    Convert PIL coordinates into Tesseract boxfile coordinates:
    in PIL, (0,0) is at the top left corner
    in tesseract boxfile format, (0,0) is at the bottom left corner
    """
    return pil_x, tif_h - pil_y
