// ---------------------------------------------------------------------------
//
// copymove.c
//
// Copyright (c) 2007-2008 John Graham-Cumming
//
// Image copy/move forgery detector using the technique described in
// 'Detection of Copy-Move Forgery in Digital Images', Fridrich,
// Soukal and Lukas
//
// http://www.ws.binghamton.edu/fridrich/Research/copymove.pdf
//
// ---------------------------------------------------------------------------
//
// Briefly the algorithm goes like this:
//
// Slide a 16x16 block across the entire image from left hand corner
// to bottom right hand corner.  For each 16x16 block perform a
// discrete cosine transform on it and then quantize the 16x16 block
// using an expanded version of the standard JPEG quantization matrix.
//
// Each quantized DCT transformed is stored in a matrix with one row
// per (x,y) position in the original image (the (x,y) being the upper
// left hand corner of the 16x16 block being examined.
//
// The resulting matrix is lexicographically sorted and then rows that
// match in the matrix are identified.  For each pair of matching rows
// (x1,y1) and (x2,y2) the shift vector (x1-x2,y1-y2) (normalized by
// swapping if necessary so that the first value is +ve) is computed
// and for each shift vector a count is kept of the number of times it
// is seen.
//
// Finally the shift vectors with a count > some threshold are
// examined, the corresponding pair of positions in the image are
// found and the 16x16 blocks they represent are highlighted.
//
// Uses the FreeImage library (http://freeimage.sf.net/) to access
// image data
//
// ---------------------------------------------------------------------------
//
// This file is part of part of copy-move
//
// copy-move is free software; you can redistribute it and/or modify
// it under the terms of the GNU General Public License as published
// by the Free Software Foundation; either version 2 of the License,
// or (at your option) any later version.
//
// copy-move is distributed in the hope that it will be useful,
// but WITHOUT ANY WARRANTY; without even the implied warranty of
// MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
// GNU General Public License for more details.
//
// You should have received a copy of the GNU General Public License
// along with shimmer; if not, write to the Free Software
// Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
//
// ---------------------------------------------------------------------------

#include <memory.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <sys/stat.h>

#include "FreeImage.h"

// This is the standard JPEG chrominance quantization matrix

double q8[8][8] = { { 4, 4, 6, 11, 24, 24, 24, 24 },
		    { 4, 5, 6, 16, 24, 24, 24, 24 },
		    { 6, 6, 14, 24, 24, 24, 24, 24 },
		    { 11, 16, 24, 24, 24, 24, 24, 24 },
		    { 24, 24, 24, 24, 24, 24, 24, 24 },
		    { 24, 24, 24, 24, 24, 24, 24, 24 },
		    { 24, 24, 24, 24, 24, 24, 24, 24 },
		    { 24, 24, 24, 24, 24, 24, 24, 24 } };

// This is the 'quality' factor.  The bigger this number the more
// 'blurred' the comparison of squares and hence the more matches you'll
// get.  You can set this using the second command-line parameter.

double quality = 0.5;

// This is the threshold below which we'll ignore matches.  There must
// be more than this many 16x16 blocks in a shift register before it'll
// be considered.  This gives the minimum number of blocks that have been
// copied together.  This can be set using the third command-line
// parameter.

int threshold = 10;

// This is expanded to a 16x16 matrix as described in Fridrich's paper
// and is filled in by code in main()

double q16[16][16];

// Used as part of the index for finding block of 16x16 pixels in the
// original image once the vectors have been sorted

struct position {
  int i;
  int x;
  int y;
};

// Height and width of the image in pixels and the number of
// overlapping 16 pixel blocks that can appear across and down in the
// image

unsigned int w;
unsigned int h;

unsigned int w16;
unsigned int h16;

// This is the matrix of 16x16 blocks after transformation and
// quantization

int * matrix;

// Function to do lexicographic compare on two rows in the matrix using
// the index.

int compare( struct position * a, struct position * b )
{
    int * m_a = &matrix[ a->i * 16 * 16 ];
    int * m_b = &matrix[ b->i * 16 * 16 ];
    
    int i;
    
    for ( i = 0; i < 16 * 16; ++i ) {
        if ( m_a[i] < m_b[i] ) {
            return -1;
        }
        if ( m_a[i] > m_b[i] ) {
            return 1;
        }
    }

    return 0;
}

int main( int argc, char * argv[] )
{
  FreeImage_Initialise(TRUE);

  if ( argc < 2 ) {
    printf( "Usage: copymove <image file> [<quality>] [<threshold>]\n" );
    return 1;
  }

  // Read the entire file that is in argv[1] and load it into
  // FreeImage for access as a bitmap

  struct stat file_stat;
  stat( argv[1], &file_stat );
  int file_size = file_stat.st_size;

  FILE * handle = fopen( argv[1], "r" );

  BYTE * bytes = malloc(file_size);
  int length = fread( bytes, 1, file_size, handle );

  fclose( handle );

  if ( argc >= 3 ) {
    quality = atof( argv[2] );
  }

  if ( argc >= 4 ) {
    threshold = atoi( argv[3] );
  }

  printf( "Set quality factor %f\n", quality );
  printf( "Set threshold %d\n", threshold );
    
  FIMEMORY * memory = FreeImage_OpenMemory( bytes, length );

  if ( !memory ) {
    return 1;
  }

  FREE_IMAGE_FORMAT format = FreeImage_GetFileTypeFromMemory( memory, 0 );
  FIBITMAP * bitmap = FreeImage_LoadFromMemory( format, memory, 0 );

  if ( !bitmap ) {
    return 1;
  }

  // We only work with black and white images, but first we convert
  // the image to 24-bit color and then we'll use the formula from
  // the paper to do the greyscale conversation.
  
  FIBITMAP * color = FreeImage_ConvertTo24Bits( bitmap );

  if ( !color ) {
    return 1;
  }
  
  // Slide a nxn window across the entire image and calculate the
  // 2-dimensional DCT for the window.  Quantize the DCT matrix
  // using the standard JPEG matrix and put the resulting matrix
  // into the matrix as a single row
  
  h = FreeImage_GetHeight( color );
  w = FreeImage_GetWidth( color );

  h16 = h - 16 + 1;
  w16 = w - 16 + 1;

  printf( "Analyzing %s (%d x %d)\n", argv[1], h, w );

  int i, j, a, d;

  // Build the extended quantization matrix

  for ( i = 0; i < 8; ++i ) {
    for ( j = 0; j < 8; ++j ) {
      q16[i][j] = q8[i][j] * 2.5;
    }
  }

  q16[0][0] = 2.0 * q8[0][0];

  for ( i = 8; i < 16; ++i ) {
    for ( j = 0; j < 8; ++j ) {
      q16[i][j] = q8[0][7] * 2.5;
    }
  }

  for ( i = 8; i < 16; ++i ) {
    for ( j = 8; j < 16; ++j ) {
      q16[i][j] = q8[7][7] * 2.5;
    }
  }
    
  for ( i = 0; i < 8; ++i ) {
    for ( j = 8; j < 16; ++j ) {
      q16[i][j] = q8[7][0] * 2.5;
    }
  }

  int bpp = FreeImage_GetBPP( color );
  bpp /= 8;
  
  double pi = 3.1415926;

  int matrix_size = w16 * h16 * 16 * 16 * sizeof( int );
  matrix = malloc( matrix_size );

  int index_size = w16 * h16 * sizeof( struct position );
  struct position * index = malloc( index_size );

  memset( matrix, 0, matrix_size );
  memset( index, 0, index_size );

  // Precompute coefficients to use in the DCT to save time

  printf( "Precomputing... " );
  fflush(0);

  int last_percent = 10;
  int i_pos = -1;

  double pre[16][16][16][16];

  int u;
  int v;

  for ( u = 0; u < 16; ++u ) {
    for ( v = 0; v < 16; ++v ) {
      for ( j = 0; j < 16; ++j ) {
	for ( i = 0; i < 16; ++i ) {
	  pre[u][v][i][j] = cos( pi / 16.0 * ( (double)i + 0.5 ) * (double)u ) *
	    cos( pi / 16.0 * ( (double)j + 0.5 ) * (double)v );
	}
      }
    }
  }
  
  double sqrt_116 = sqrt(1.0/16.0);
  double sqrt_216 = sqrt(2.0/16.0);

  printf( "done.\nBuilding DCT transformed matrix... " );
  fflush(0);

  double pixels[h][w];
  for (i = 0; i < h; i++) {
      BYTE *bits = FreeImage_GetScanLine(color, i);
      for (j = 0; j < w; ++j) {
          BYTE *bit = bits + bpp * j;
          double pixel = (double)bit[FI_RGBA_RED] * 0.299
              + (double)bit[FI_RGBA_GREEN] * 0.587
              + (double)bit[FI_RGBA_BLUE] * 0.114;
          pixel -= 128;
          pixel = round(pixel);
          pixels[i][j] = pixel;
      }
  }

  for ( a = 0; a < w16; ++a ) {
    for ( d = 0; d < h16; ++d ) {
      ++i_pos;
      index[i_pos].i = i_pos;
      index[i_pos].x = a;
      index[i_pos].y = d;

      if ( ( ( 100 * ( a * h16 +d ) ) / ( w16 * h16 ) )>last_percent ) {
	printf( "%d%% ", last_percent );
	fflush(0);
	last_percent += 10;
      }

      // The result of the DCT is stored in this matrix and is
      // computed as we scan the image.  First it is set to 0.

      double dct[16][16];

      for ( i = 0; i < 16; ++i ) {
	for ( j = 0; j < 16; ++j ) {
	  dct[i][j] = 0;
	}
      }

      // Compute one step of the DCT based on the pixel
      // that we are looking at

      for ( u = 0; u < 16; ++u ) {
	for ( v = 0; v < 16; ++v ) {
	  for ( j = 0; j < 16; ++j ) {
//	    BYTE * bits = FreeImage_GetScanLine( color, j + d );
//	    bits += bpp * a;
	    for ( i = 0; i < 16; ++i ) {
                double pixel = pixels[j + d][a + i];

	      dct[u][v] += pixel * pre[u][v][i][j];
//	      bits += bpp;
	    }
	  }
	}
      }

      // Here the DCT has been computed and needs to be quantized

      for ( u = 0; u < 16; ++u ) {
	for ( v = 0; v < 16; ++v ) {
	  dct[u][v] *= (u==0)?sqrt_116:sqrt_216;
	  dct[u][v] *= (v==0)?sqrt_116:sqrt_216;
	  dct[u][v] /= quality;
	  dct[u][v] /= q16[u][v];
	  dct[u][v] = round( dct[u][v] );
	}
      }

      // Now take the resulting quantized DCT matrix and insert
      // it into the matrix
      
      for ( i = 0; i < 16; ++i ) {
	for ( j = 0; j < 16; ++j ) {
	  matrix[ i_pos * 16 * 16 + j + 16 * i ] =
	    (int)dct[i][j];
	}
      }
    }
  }

  printf( "done\nSorting index into lexicographic order... " );

  // At this point the matrix has been created and now needs to
  // be sorted and copied sections must be detected

  qsort( &index[0], w16 * h16, 
	 sizeof( struct position ), (void*)&compare );

  printf( "done\nBuilding shift vectors... " );
  fflush(0);

  // Build shift vectors the recognize blocks of identical pixels

  int * shift = malloc( sizeof( int ) * w * h * 2 );

  for ( i = 0; i < w; ++i ) {
    for ( j = 0; j < h*2; ++j ) {
      shift[j * w + i] = 0;
    }
  }
  
  last_percent = 10;

  for ( i = 0; i < w16 * h16 - 1; ++i ) {
    if ( ( 100 * i / ( w16 * h16 -1 ) ) > last_percent ) {
      printf( "%d%% ", last_percent );
      fflush(0);
      last_percent += 10;
    }
    
    if ( compare( &index[i], &index[i+1] ) == 0 ) {
      int sx = index[i].x - index[i+1].x;
      int sy = index[i].y - index[i+1].y;
      
      if ( sx < 0 ) {
	sx = -sx;
	sy = -sy;
      }
      
      sy += h;
      
      ++shift[sy * w + sx];
    }
  }

  printf( "done\nCreating cloned images... " );
  fflush(0);

  // Duplicate the original color image and shade areas of the image
  // that appear to be duplicated by finding shift vectors with a
  // count above the threshold
  
  last_percent = 10;

  FIBITMAP * total = FreeImage_Clone( color );

  for ( i = 0; i < w; ++i ) {
    for ( j = 0; j < h*2; ++j ) {
      if ( ( 100 * (i+j) / ( w * ( h + h ) ) ) > last_percent ) {
	printf( "%d%% ", last_percent );
	fflush(0);
	last_percent += 10;
      }
      
      if ( ( ( i > 16 ) || ( ( abs(j-h) > 16 ) ) ) &&
	   ( shift[j * w + i] > threshold ) ) {
	printf( "Shift vector (%d,%d) has count %d\n", i, j - h,
		shift[j * w + i] );

	FIBITMAP * clone = FreeImage_Clone( color );

	int sx = i;
	int sy = j - h;

	int k;
	for ( k = 0; k < w16 * h16 - 1; ++k ) {
	  if ( compare( &index[k], &index[k+1] ) == 0 ) {
	    int sxx = index[k].x - index[k+1].x;
	    int syy = index[k].y - index[k+1].y;
	    if ( sxx < 0 ) {
	      sxx = -sxx;
	      syy = -syy;
	    }
	    
	    if ( sx == sxx ) {
	      if ( sy == syy ) {
		int x; 
		int y;
		int c;
		
#define max(a,b) (((a)>(b))?a:b)
#define min(a,b) (((a)<(b))?a:b)

		for ( c = k; c < k+2; ++c ) {
		  for ( x = index[c].x; x < index[c].x + 16; ++x ) {
		    for ( y = index[c].y; y < index[c].y + 16; ++y ) {
		      RGBQUAD pixel;
		      FreeImage_GetPixelColor( color, x, y, &pixel );
		      if ( index[k].x < index[k+1].x ) {
			if ( c == k ) {
			  pixel.rgbRed = 255;
			} else {
			  pixel.rgbBlue = 255;
			}
		      } else {
			if ( c != k ) {
			  pixel.rgbRed = 255;
			} else {
			  pixel.rgbBlue = 255;
			}
		      }
		      FreeImage_SetPixelColor( clone, x, y, &pixel );
		      FreeImage_SetPixelColor( total, x, y, &pixel );
		    }
		  }
		}
	      }
	    }
	  }
	}
	
	char output[1000];
	sprintf( output, "%s-%d=%d.png", argv[1], i, j-h );
	  
	FreeImage_Save( FIF_PNG, clone, output, PNG_DEFAULT );
	FreeImage_Unload( clone );
      }
    }
  }

  char output[1000];
  sprintf( output, "%s-total.png", argv[1] );
  FreeImage_Save( FIF_PNG, total, output, PNG_DEFAULT );
  
  FreeImage_Unload( total );
  FreeImage_Unload( color );
  FreeImage_Unload( bitmap );
  FreeImage_DeInitialise();

  printf( "done\n" );

  free( bytes );
  free( matrix );
  free( shift );
  free( index );

  return 0;
}

