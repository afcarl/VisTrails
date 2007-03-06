############################################################################
##
## Copyright (C) 2006-2007 University of Utah. All rights reserved.
##
## This file is part of VisTrails.
##
## This file may be used under the terms of the GNU General Public
## License version 2.0 as published by the Free Software Foundation
## and appearing in the file LICENSE.GPL included in the packaging of
## this file.  Please review the following to ensure GNU General Public
## Licensing requirements will be met:
## http://www.opensource.org/licenses/gpl-license.php
##
## If you are unsure which license is appropriate for your use (for
## instance, you are interested in developing a commercial derivative
## of VisTrails), please contact us at vistrails@sci.utah.edu.
##
## This file is provided AS IS with NO WARRANTY OF ANY KIND, INCLUDING THE
## WARRANTY OF DESIGN, MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE.
##
############################################################################
#  ITK package for VisTrails

version = '0.1'

try:
    import itk
except ImportError:
    raise PackageError("This package requires ITK and WrapITK")

import core.modules
import core.modules.module_registry

from ITK import ITK, PixelType
from PixelTypes import *
from Image import *
from ImageReader import *
from Filters import *
from FeatureExtractionFilters import *
from IntensityFilters import *
from SegmentationFilters import *
from SelectionFilters import *

def initialize(*args, **keywords):
    reg = core.modules.module_registry
    basic = core.modules.basic_modules

    reg.addModule(ITK)
    reg.addModule(Index2D)
    reg.addInputPort(Index2D, "X Index", (basic.Integer, 'X Index'))
    reg.addInputPort(Index2D, "Y Index", (basic.Integer, 'Y Index'))
    reg.addOutputPort(Index2D, "Index", (Index2D, 'Index'))

    reg.addModule(Index3D)
    reg.addInputPort(Index3D, "X Index", (basic.Integer, 'X Index'))
    reg.addInputPort(Index3D, "Y Index", (basic.Integer, 'Y Index'))
    reg.addInputPort(Index3D, "Z Index", (basic.Integer, 'Z Index'))
    reg.addOutputPort(Index3D, "Index", (Index3D, 'Index'))

    reg.addModule(Size)
    reg.addInputPort(Size, "Dimension", (basic.Integer, 'Dimension'))
    reg.addInputPort(Size, "Element 1", (basic.Integer, 'Element 1'))
    reg.addInputPort(Size, "Element 2", (basic.Integer, 'Element 2'))
    reg.addInputPort(Size, "Element 3", (basic.Integer, 'Element 3'))
    reg.addOutputPort(Size, "Size", (Size, 'Size'))

    reg.addModule(Region)
    reg.addInputPort(Region, "Dimension", (basic.Integer, 'Dimension'))
    reg.addInputPort(Region, "Size", (Size, 'Size'))
    reg.addInputPort(Region, "Input 2D Index", (Index2D, 'Input 2D Index'))
    reg.addInputPort(Region, "Input 3D Index", (Index3D, 'Input 3D Index'), True)
    reg.addOutputPort(Region, "Region", (Region, 'Region'))

    reg.addModule(PixelType)

    reg.addModule(PixelTypeFloat)
    reg.addOutputPort(PixelTypeFloat, "Pixel Type", (PixelType, 'Pixel Type'))

    reg.addModule(PixelTypeUnsignedChar)
    reg.addOutputPort(PixelTypeUnsignedChar, "Pixel Type", (PixelType, 'Pixel Type'))

    reg.addModule(PixelTypeUnsignedShort)
    reg.addOutputPort(PixelTypeUnsignedShort, "Pixel Type", (PixelType, 'Pixel Type'))

    reg.addModule(PixelTypeRGB)
    reg.addOutputPort(PixelTypeRGB, "Pixel Type", (PixelType, 'Pixel Type'))

    reg.addModule(Image)
    reg.addInputPort(Image, "Pixel Type", (PixelType, 'Pixel Type'))
    reg.addInputPort(Image, "Dimension", (basic.Integer, 'Dimension'))
    reg.addInputPort(Image, "Image", (Image, 'Image'))
    reg.addOutputPort(Image, "Image Pixel Type", (PixelType, 'Image Pixel Type'))
    reg.addOutputPort(Image, "Image Dimension", (basic.Integer, 'Image Dimension'))
    reg.addOutputPort(Image, "Output Image", (Image, 'Output Image'))

    reg.addModule(ImageReader)
    reg.addInputPort(ImageReader, "Filename", (basic.String, 'Filename'))
    reg.addInputPort(ImageReader, "Pixel Type", (PixelType, 'Pixel Type'))
    reg.addInputPort(ImageReader, "Dimension", (basic.Integer, 'Dimension'))
    reg.addOutputPort(ImageReader, "Image", (Image, 'Image'))
    reg.addOutputPort(ImageReader, "Reader", (ImageReader, 'Reader'))

    reg.addModule(DICOMReader)
    reg.addInputPort(DICOMReader, "Directory", (basic.String, 'Directory'))
    reg.addInputPort(DICOMReader, "Dimension", (basic.Integer, 'Dimension'))
    reg.addOutputPort(DICOMReader, "Image Series", (Image, 'Image Series'))

    reg.addModule(ImageToFile)
    reg.addInputPort(ImageToFile, "Suffix", (basic.String, 'Suffix'))
    reg.addInputPort(ImageToFile, "Pixel Type", (PixelType, 'Pixel Type'))
    reg.addInputPort(ImageToFile, "Dimension", (basic.Integer, 'Dimension'))
    reg.addInputPort(ImageToFile, "Image", (Image, 'Image'))
    reg.addOutputPort(ImageToFile, "File", (basic.File, 'File'))

    reg.addModule(Filter, "Image Filters")
    reg.addModule(FeatureFilter, "Feature Extraction Filters")
    reg.addModule(GradientMagnitudeRecursiveGaussianImageFilter)
    reg.addInputPort(GradientMagnitudeRecursiveGaussianImageFilter, "Input Filter", (Filter, 'Input Filter'))
    reg.addInputPort(GradientMagnitudeRecursiveGaussianImageFilter, "Input Image", (Image, 'Input Image'))
    reg.addInputPort(GradientMagnitudeRecursiveGaussianImageFilter, "Input PixelType", (PixelType, 'Input PixelType'))
    reg.addInputPort(GradientMagnitudeRecursiveGaussianImageFilter, "Output PixelType", (PixelType, 'Output PixelType'), True)
    reg.addInputPort(GradientMagnitudeRecursiveGaussianImageFilter, "Dimension", (basic.Integer, 'Dimension'))
    reg.addInputPort(GradientMagnitudeRecursiveGaussianImageFilter, "Sigma", (basic.Float, 'Sigma'))
    reg.addOutputPort(GradientMagnitudeRecursiveGaussianImageFilter, "Output Image", (Image, 'Output Image'))
    reg.addOutputPort(GradientMagnitudeRecursiveGaussianImageFilter, "Filter", (Filter, 'Filter'), True)
    reg.addOutputPort(GradientMagnitudeRecursiveGaussianImageFilter, "Output PixelType", (PixelType, 'Output PixelType'), True)

    reg.addModule(IntensityFilter, "Image Intensity Filters")
    reg.addModule(RescaleIntensityImageFilter)
    reg.addInputPort(RescaleIntensityImageFilter, "Input Filter", (Filter, 'Input Filter'), True)
    reg.addInputPort(RescaleIntensityImageFilter, "Input Image", (Image, 'Input Image'))
    reg.addInputPort(RescaleIntensityImageFilter, "Input PixelType", (PixelType, 'Input PixelType'))
    reg.addInputPort(RescaleIntensityImageFilter, "Output PixelType", (PixelType, 'Output PixelType'), True)
    reg.addInputPort(RescaleIntensityImageFilter, "Dimension", (basic.Integer, 'Dimension'))
    reg.addInputPort(RescaleIntensityImageFilter, "Minimum", (basic.Integer, 'Minimum'))
    reg.addInputPort(RescaleIntensityImageFilter, "Maximum", (basic.Integer, 'Maximum'))
    reg.addOutputPort(RescaleIntensityImageFilter, "Output Image", (Image, 'Output Image'))
    reg.addOutputPort(RescaleIntensityImageFilter, "Filter", (Filter, 'Filter'), True)
    reg.addOutputPort(RescaleIntensityImageFilter, "Output PixelType", (PixelType, 'Output PixelType'), True)

    reg.addModule(SegmentationFilter, "Segmentation Filters")
    reg.addModule(IsolatedWatershedImageFilter)
    reg.addInputPort(IsolatedWatershedImageFilter, "Input Image", (Image, 'Input Image'))
    reg.addInputPort(IsolatedWatershedImageFilter, "Input PixelType", (PixelType, 'Input PixelType'))
    reg.addInputPort(IsolatedWatershedImageFilter, "Dimension", (basic.Integer, 'Dimension'))
    reg.addInputPort(IsolatedWatershedImageFilter, "Seed1", (Index2D, 'Seed 1 Location'))

    reg.addInputPort(IsolatedWatershedImageFilter, "Output PixelType", (PixelType, 'Output PixelType'), True)
    reg.addInputPort(IsolatedWatershedImageFilter, "Threshold", (basic.Float, 'Threshold'), True)
    reg.addInputPort(IsolatedWatershedImageFilter, "Seed2", (Index2D, 'Seed 2 Location'), True)
    reg.addInputPort(IsolatedWatershedImageFilter, "ReplaceValue1", (basic.Float, 'Replacement Value 1'), True);
    reg.addInputPort(IsolatedWatershedImageFilter, "ReplaceValue2", (basic.Float, 'Replacement Value 2'), True);

    reg.addOutputPort(IsolatedWatershedImageFilter, "Output Image", (Image, 'Output Image'))
    reg.addOutputPort(IsolatedWatershedImageFilter, "Output PixelType", (PixelType, 'Output PixelType'), True)

    reg.addModule(SelectionFilter, "Image Selection Filters")
    reg.addModule(CastImageFilter)
    reg.addInputPort(CastImageFilter, "Input Image", (Image, 'Input Image'))
    reg.addInputPort(CastImageFilter, "Dimension", (basic.Integer, 'Dimension'))
    reg.addInputPort(CastImageFilter, "Input PixelType", (PixelType, 'Input PixelType'))
    reg.addInputPort(CastImageFilter, "Output PixelType", (PixelType, 'Output PixelType'))
    reg.addOutputPort(CastImageFilter, "Output Image", (Image, 'Output Image'))
    reg.addOutputPort(CastImageFilter, "Output PixelType", (PixelType, 'Output PixelType'), True)
    reg.addOutputPort(CastImageFilter, "Dimension", (basic.Integer, 'Dimension'), True)

    reg.addModule(RegionOfInterestImageFilter, "RegionOfInterestFilter")
    reg.addInputPort(RegionOfInterestImageFilter, "Input Dimension", (basic.Integer, 'Input Dimension'))
    reg.addInputPort(RegionOfInterestImageFilter, "Output Dimension", (basic.Integer, 'Output Dimension'))
    reg.addInputPort(RegionOfInterestImageFilter, "Input PixelType", (PixelType, 'Input PixelType'))
    reg.addInputPort(RegionOfInterestImageFilter, "Output PixelType", (PixelType, 'Output PixelType'), True)
    reg.addInputPort(RegionOfInterestImageFilter, "Input 2D Index", (Index2D, 'Input 2D Index'))
    reg.addInputPort(RegionOfInterestImageFilter, "Input 3D Index", (Index3D, 'Input 3D Index'), True)
    reg.addInputPort(RegionOfInterestImageFilter, "Region Size", (Size, 'Region Size'))
    reg.addInputPort(RegionOfInterestImageFilter, "Input Image", (Image, 'Input Image'))
    reg.addInputPort(RegionOfInterestImageFilter, "Input Region", (Region, 'Input Region'), True)
    reg.addOutputPort(RegionOfInterestImageFilter, "Output Image", (Image, 'Output Image'))
    reg.addOutputPort(RegionOfInterestImageFilter, "Output PixelType", (PixelType, 'Output PixelType'), True)
    reg.addOutputPort(RegionOfInterestImageFilter, "Filter", (Filter, 'Filter'), True)
    reg.addOutputPort(RegionOfInterestImageFilter, "Output Dimension", (basic.Integer, 'Output Dimension'))

    reg.addModule(ExtractImageFilter)
    reg.addInputPort(ExtractImageFilter, "Input Volume", (Image, 'Input Image'))
    reg.addInputPort(ExtractImageFilter, "Input Dimension", (basic.Integer, 'Input Dimension'))
    reg.addInputPort(ExtractImageFilter, "Output Dimension", (basic.Integer, 'Output Dimension'))
    reg.addInputPort(ExtractImageFilter, "Input PixelType", (PixelType, 'Input PixelType'))
    reg.addInputPort(ExtractImageFilter, "Extraction Region", (Region, 'Extraction Region'))
    reg.addOutputPort(ExtractImageFilter, "Output Image", (Image, 'Output Image'))
    reg.addOutputPort(ExtractImageFilter, "Output PixelType", (PixelType, 'Output PixelType'), True)
    reg.addOutputPort(ExtractImageFilter, "Dimension", (basic.Integer, 'Dimension'), True)