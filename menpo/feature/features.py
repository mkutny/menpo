from __future__ import division
import itertools
import numpy as np
scipy_gaussian_filter = None  # expensive

from .base import ndfeature, winitfeature
from .gradient import gradient_cython
from .windowiterator import WindowIterator, WindowIteratorResult


@ndfeature
def gradient(pixels, fast2d=True):
    r"""
    Calculates the gradient of an input image. The image is assumed to have
    channel information on the first axis. In the case of multiple channels,
    it returns the gradient over each axis over each channel as the first axis.

    Parameters
    ----------
    pixels : `ndarray`, shape (C, X, Y, ..., Z)
        An array where the first dimension is interpreted as channels. This
        means an N-dimensional image is represented by an N+1 dimensional
        array.

    fast2d : bool, optional
        Enables faster gradient computation for 2-dimensional
        multichannel image.

    Returns
    -------
    gradient : ndarray, shape (C * length([X, Y, ..., Z], X, Y, ..., Z))
        The gradient over each axis over each channel. Therefore, the
        first axis of the gradient of a 2D, single channel image, will have
        length `2`. The first axis of the gradient of a 2D, 3-channel image,
        will have length `6`, the ordering being [Rd_x, Rd_y, Gd_x, Gd_y,
        Bd_x, Bd_y].

    """
    if fast2d and (len(pixels.shape) is 3):
        return gradient_cython(pixels)
    else:
        grad_per_dim_per_channel = [np.gradient(g) for g in pixels]
        # Flatten out the separate dims
        grad_per_channel = list(itertools.chain.from_iterable(
            grad_per_dim_per_channel))
        # Add a channel axis for broadcasting
        grad_per_channel = [g[None, ...] for g in grad_per_channel]
        # Concatenate gradient list into an array (the new_image)
        return np.concatenate(grad_per_channel, axis=0)


@ndfeature
def gaussian_filter(pixels, sigma):
    global scipy_gaussian_filter
    if scipy_gaussian_filter is None:
        from scipy.ndimage import gaussian_filter as scipy_gaussian_filter
    output = np.empty(pixels.shape)
    for dim in range(pixels.shape[0]):
        scipy_gaussian_filter(pixels[dim, ...], sigma, output=output[dim, ...])
    return output


# TODO: Needs fixing ...
@winitfeature
def hog(pixels, mode='dense', algorithm='dalaltriggs', num_bins=9,
        cell_size=8, block_size=2, signed_gradient=True, l2_norm_clip=0.2,
        window_height=1, window_width=1, window_unit='blocks',
        window_step_vertical=1, window_step_horizontal=1,
        window_step_unit='pixels', padding=True, verbose=False):
    r"""
    Computes a 2-dimensional HOG features image with k number of channels, of
    size `(M, N, C)` and data type `np.float`.

    Parameters
    ----------
    mode : 'dense' or 'sparse'
        The 'sparse' case refers to the traditional usage of HOGs, so default
        parameters values are passed to the ImageWindowIterator.
        The sparse case of 'dalaltriggs' algorithm sets the window height
        and width equal to block size and the window step horizontal and
        vertical equal to cell size. The sparse case of 'zhuramanan'
        algorithm sets the window height and width equal to 3 times the
        cell size and the window step horizontal and vertical equal to cell
        size. In the 'dense' case, the user can change the window_height,
        window_width, window_unit, window_step_vertical,
        window_step_horizontal, window_step_unit, and padding to completely
        customize the HOG calculation.

    window_height : float
        Defines the height of the window for the ImageWindowIterator
        object. The metric unit is defined by window_unit.

    window_width : float
        Defines the width of the window for the ImageWindowIterator object.
        The metric unit is defined by window_unit.

    window_unit : 'blocks' or 'pixels'
        Defines the metric unit of the window_height and window_width
        parameters for the ImageWindowIterator object.

    window_step_vertical : float
        Defines the vertical step by which the window is moved, thus it
        controls the features density. The metric unit is defined by
        window_step_unit.

    window_step_horizontal : float
        Defines the horizontal step by which the window is moved, thus it
        controls the features density. The metric unit is defined by
        window_step_unit.

    window_step_unit : 'pixels' or 'cells'
        Defines the metric unit of the window_step_vertical and
        window_step_horizontal parameters.

    padding : bool
        Enables/disables padding for the close-to-boundary windows in the
        ImageWindowIterator object. When padding is enabled,
        the out-of-boundary pixels are set to zero.

    algorithm : 'dalaltriggs' or 'zhuramanan'
        Specifies the algorithm used to compute HOGs.

    cell_size : float
        Defines the cell size in pixels. This value is set to both the width
        and height of the cell. This option is valid for both algorithms.

    block_size : float
        Defines the block size in cells. This value is set to both the width
        and height of the block. This option is valid only for the
        'dalaltriggs' algorithm.

    num_bins : float
        Defines the number of orientation histogram bins. This option is
        valid only for the 'dalaltriggs' algorithm.

    signed_gradient : bool
        Flag that defines whether we use signed or unsigned gradient angles.
        This option is valid only for the 'dalaltriggs' algorithm.

    l2_norm_clip : float
        Defines the clipping value of the gradients' L2-norm. This option is
        valid only for the 'dalaltriggs' algorithm.

    constrain_landmarks : bool
        Flag that if enabled, it constrains landmarks that ended up outside of
        the features image bounds.

    verbose : bool
        Flag to print HOG related information.

    Raises
    -------
    ValueError
        HOG features mode must be either dense or sparse
    ValueError
        Algorithm must be either dalaltriggs or zhuramanan
    ValueError
        Number of orientation bins must be > 0
    ValueError
        Cell size (in pixels) must be > 0
    ValueError
        Block size (in cells) must be > 0
    ValueError
        Value for L2-norm clipping must be > 0.0
    ValueError
        Window height must be >= block size and <= image height
    ValueError
        Window width must be >= block size and <= image width
    ValueError
        Window unit must be either pixels or blocks
    ValueError
        Horizontal window step must be > 0
    ValueError
        Vertical window step must be > 0
    ValueError
        Window step unit must be either pixels or cells
    """
    # TODO: This is a temporal fix
    # flip axis
    pixels = np.rollaxis(pixels, 0, len(pixels.shape))

    # Parse options
    if mode not in ['dense', 'sparse']:
        raise ValueError("HOG features mode must be either dense or sparse")
    if algorithm not in ['dalaltriggs', 'zhuramanan']:
        raise ValueError("Algorithm must be either dalaltriggs or zhuramanan")
    if num_bins <= 0:
        raise ValueError("Number of orientation bins must be > 0")
    if cell_size <= 0:
        raise ValueError("Cell size (in pixels) must be > 0")
    if block_size <= 0:
        raise ValueError("Block size (in cells) must be > 0")
    if l2_norm_clip <= 0.0:
        raise ValueError("Value for L2-norm clipping must be > 0.0")
    if mode == 'dense':
        if window_unit not in ['pixels', 'blocks']:
            raise ValueError("Window unit must be either pixels or blocks")
        window_height_temp = window_height
        window_width_temp = window_width
        if window_unit == 'blocks':
            window_height_temp = window_height * block_size * cell_size
            window_width_temp = window_width * block_size * cell_size
        if (window_height_temp < block_size * cell_size or
            window_height_temp > pixels.shape[0]):
            raise ValueError("Window height must be >= block size and <= "
                             "image height")
        if (window_width_temp < block_size*cell_size or
            window_width_temp > pixels.shape[1]):
            raise ValueError("Window width must be >= block size and <= "
                             "image width")
        if window_step_horizontal <= 0:
            raise ValueError("Horizontal window step must be > 0")
        if window_step_vertical <= 0:
            raise ValueError("Vertical window step must be > 0")
        if window_step_unit not in ['pixels', 'cells']:
            raise ValueError("Window step unit must be either pixels or cells")

    # Correct input image_data
    pixels = np.asfortranarray(pixels)
    pixels *= 255.

    # Dense case
    if mode == 'dense':
        # Iterator parameters
        if algorithm == 'dalaltriggs':
            algorithm = 1
            if window_unit == 'blocks':
                block_in_pixels = cell_size * block_size
                window_height = np.uint32(window_height * block_in_pixels)
                window_width = np.uint32(window_width * block_in_pixels)
            if window_step_unit == 'cells':
                window_step_vertical = np.uint32(window_step_vertical *
                                                 cell_size)
                window_step_horizontal = np.uint32(window_step_horizontal *
                                                   cell_size)
        elif algorithm == 'zhuramanan':
            algorithm = 2
            if window_unit == 'blocks':
                block_in_pixels = 3 * cell_size
                window_height = np.uint32(window_height * block_in_pixels)
                window_width = np.uint32(window_width * block_in_pixels)
            if window_step_unit == 'cells':
                window_step_vertical = np.uint32(window_step_vertical *
                                                 cell_size)
                window_step_horizontal = np.uint32(window_step_horizontal *
                                                   cell_size)
        iterator = WindowIterator(pixels, window_height, window_width,
                                  window_step_horizontal,
                                  window_step_vertical, padding)
    # Sparse case
    else:
        # Create iterator
        if algorithm == 'dalaltriggs':
            algorithm = 1
            window_size = cell_size * block_size
            step = cell_size
        else:
            algorithm = 2
            window_size = 3 * cell_size
            step = cell_size
        iterator = WindowIterator(pixels, window_size, window_size, step,
                                  step, False)
    # Print iterator's info
    if verbose:
        print(iterator)
    # Compute HOG
    hog_descriptor = iterator.HOG(algorithm, num_bins, cell_size, block_size,
                                  signed_gradient, l2_norm_clip, verbose)
    # TODO: This is a temporal fix
    # flip axis
    hog_descriptor = WindowIteratorResult(
        np.ascontiguousarray(np.rollaxis(hog_descriptor.pixels, -1)),
        hog_descriptor.centres)
    return hog_descriptor

    # store parameters
    # hog_image.hog_parameters = {'mode': mode, 'algorithm': algorithm,
    #                             'num_bins': num_bins,
    #                             'cell_size': cell_size,
    #                             'block_size': block_size,
    #                             'signed_gradient': signed_gradient,
    #                             'l2_norm_clip': l2_norm_clip,
    #
    #                             'window_height': window_height,
    #                             'window_width': window_width,
    #                             'window_unit': window_unit,
    #                             'window_step_vertical': window_step_vertical,
    #                             'window_step_horizontal':
    #                                 window_step_horizontal,
    #                             'window_step_unit': window_step_unit,
    #                             'padding': padding,
    #
    #                             'original_image_height':
    #                                 self._image.pixels.shape[0],
    #                             'original_image_width':
    #                                 self._image.pixels.shape[1],
    #                             'original_image_channels':
    #                                 self._image.pixels.shape[2]}


@ndfeature
def igo(pixels, double_angles=False, fast2d=True, verbose=False):
    r"""
    Represents a 2-dimensional IGO features image with N*C number of
    channels, where N is the number of channels of the original image and
    C=[2,4] depending on whether double angles are used.

    Parameters
    ----------
    pixels :  ndarray
        The pixel data for the image, where the last axis represents the
        number of channels.

    double_angles : bool
        Assume that phi represents the gradient orientations. If this flag
        is disabled, the features image is the concatenation of cos(phi)
        and sin(phi), thus 2 channels. If it is enabled, the features image
        is the concatenation of cos(phi), sin(phi), cos(2*phi), sin(2*phi),
        thus 4 channels.

    verbose : bool
        Flag to print IGO related information.

    Raises
    -------
    ValueError
        Image has to be 2D in order to extract IGOs.

    """
    # check number of dimensions
    if len(pixels.shape) != 3:
        raise ValueError('IGOs only work on 2D images. Expects image data '
                         'to be 3D, channels + shape.')
    # feature channels per image channel
    feat_channels = 2
    if double_angles:
        feat_channels = 4
    # compute gradients
    grad = gradient(pixels, fast2d=fast2d)
    # compute angles
    grad_orient = np.angle(grad[1::2, ...] + 1j * grad[::2, ...])
    # compute igo image
    igo_pixels = np.empty((pixels.shape[0] * feat_channels,
                           pixels.shape[1], pixels.shape[2]))
    igo_pixels[1::feat_channels, ...] = np.cos(grad_orient)
    igo_pixels[::feat_channels, ...] = np.sin(grad_orient)
    if double_angles:
        igo_pixels[3::feat_channels, ...] = np.cos(2 * grad_orient)
        igo_pixels[2::feat_channels, ...] = np.sin(2 * grad_orient)

    # print information
    if verbose:
        info_str = "IGO Features:\n"
        info_str = "{}  - Input image is {}W x {}H with {} channels.\n".format(
            info_str, pixels.shape[2], pixels.shape[1],
            pixels.shape[0])
        if double_angles:
            info_str = "{}  - Double angles are enabled.\n".format(info_str)
        else:
            info_str = "{}  - Double angles are disabled.\n".format(info_str)
        info_str = "{}Output image size {}W x {}H with {} channels.".format(
            info_str, igo_pixels.shape[2], igo_pixels.shape[1],
            igo_pixels.shape[0])
        print(info_str)
    return igo_pixels

    # store parameters
    # igo_image.igo_parameters = {'double_angles': double_angles,
    #
    #                             'original_image_height':
    #                                 self._image.pixels.shape[0],
    #                             'original_image_width':
    #                                 self._image.pixels.shape[1],
    #                             'original_image_channels':
    #                                 self._image.pixels.shape[2]}


@ndfeature
def es(image_data, fast2d=True, verbose=False):
    r"""
    Represents a 2-dimensional Edge Structure (ES) features image with N*C
    number of channels, where N is the number of channels of the original
    image and C=2. The output object's class is either MaskedImage or Image
    depending on the original image.

    Parameters
    ----------
    image_data :  ndarray
        The pixel data for the image, where the last axis represents the
        number of channels.
    verbose : bool
        Flag to print ES related information.

        Default: False

    Raises
    -------
    ValueError
        Image has to be 2D in order to extract ES features.
    """
    # check number of dimensions
    if len(image_data.shape) != 3:
        raise ValueError('ES features only work on 2D images. Expects '
                         'image data to be 3D, channels + shape.')
    # feature channels per image channel
    feat_channels = 2
    # compute gradients
    grad = gradient(image_data, fast2d=fast2d)
    # compute magnitude
    grad_abs = np.abs(grad[::2, ...] + 1j * grad[1::2, ...])
    # compute es image
    grad_abs = grad_abs + np.median(grad_abs)
    es_pixels = np.empty((image_data.shape[0] * feat_channels,
                          image_data.shape[1], image_data.shape[2]))
    es_pixels[::feat_channels, ...] = grad[::2, ...] / grad_abs
    es_pixels[1::feat_channels, ...] = grad[1::2, ...] / grad_abs
    # print information
    if verbose:
        info_str = "ES Features:\n"
        info_str = "{}  - Input image is {}W x {}H with {} channels.\n".format(
            info_str, image_data.shape[2], image_data.shape[1],
            image_data.shape[0])
        info_str = "{}Output image size {}W x {}H with {} channels.".format(
            info_str, es_pixels.shape[2], es_pixels.shape[1],
            es_pixels.shape[0])
        print(info_str)
    return es_pixels

    # store parameters
    # es_image.es_parameters = {'original_image_height':
    #                               self._image.pixels.shape[0],
    #                           'original_image_width':
    #                               self._image.pixels.shape[1],
    #                           'original_image_channels':
    #                               self._image.pixels.shape[2]}


@ndfeature
def daisy(pixels, step=1, radius=15, rings=2, histograms=2, orientations=8,
          normalization='l1', sigmas=None, ring_radii=None,
          fast2d=True, verbose=False):
    r"""
    Computes a 2-dimensional Daisy features image with N*C number of channels,
    where N is the number of channels of the original image and C is the
    feature channels determined by the input options. Specifically,
    C = (rings * histograms + 1) * orientations.

    Parameters
    ----------
    pixels :  ndarray
        The pixel data for the image, where the last axis represents the
        number of channels.

    step : `int`, Optional
        The sampling step that defines the density of the output image.

    radius : `int`, Optional
        The radius (in pixels) of the outermost ring.

    rings : `int`, Optional
        The number of rings to be used.

    histograms : `int`, Optional
        The number of histograms sampled per ring.

    orientations : `int`, Optional
        The number of orientations (bins) per histogram.

    normalization : [ 'l1', 'l2', 'daisy', None ], Optional
        It defines how to normalize the descriptors
        If 'l1' then L1-normalization is applied at each descriptor.
        If 'l2' then L2-normalization is applied at each descriptor.
        If 'daisy' then L2-normalization is applied at individual histograms.
        If None then no normalization is employed.

    sigmas : 1D array of `float`, Optional
        Standard deviation of spatial Gaussian smoothing for the centre
        histogram and for each ring of histograms. The array of sigmas should
        be sorted from the centre and out. I.e. the first sigma value defines
        the spatial smoothing of the centre histogram and the last sigma value
        defines the spatial smoothing of the outermost ring. Specifying sigmas
        overrides the following parameter.

            ``rings = len(sigmas) - 1``

    ring_radii : 1D array of `int`, Optional
        Radius (in pixels) for each ring. Specifying ring_radii overrides the
        following two parameters.

            ``rings = len(ring_radii)``
            ``radius = ring_radii[-1]``

        If both sigmas and ring_radii are given, they must satisfy the
        following predicate since no radius is needed for the centre
        histogram.

            ``len(ring_radii) == len(sigmas) + 1``

    verbose : `bool`
        Flag to print Daisy related information.

    Raises
    -------
    ValueError
        `len(sigmas)-1 != len(ring_radii)`
    ValueError
        Invalid normalization method.
    """
    from menpo.external.skimage._daisy import _daisy

    # Parse options
    if sigmas is not None and ring_radii is not None \
            and len(sigmas) - 1 != len(ring_radii):
        raise ValueError('`len(sigmas)-1 != len(ring_radii)`')
    if ring_radii is not None:
        rings = len(ring_radii)
        radius = ring_radii[-1]
    if sigmas is not None:
        rings = len(sigmas) - 1
    if sigmas is None:
        sigmas = [radius * (i + 1) / float(2 * rings) for i in range(rings)]
    if ring_radii is None:
        ring_radii = [radius * (i + 1) / float(rings) for i in range(rings)]
    if normalization is None:
        normalization = 'off'
    if normalization not in ['l1', 'l2', 'daisy', 'off']:
        raise ValueError('Invalid normalization method.')

    # Compute daisy features
    daisy_descriptor = _daisy(pixels, step=step, radius=radius, rings=rings,
                              histograms=histograms, orientations=orientations,
                              normalization=normalization, sigmas=sigmas,
                              ring_radii=ring_radii, fast2d=fast2d)

    # print information
    if verbose:
        info_str = "Daisy Features:\n"
        info_str = "{}  - Input image is {}W x {}H with {} channels.\n".format(
            info_str, pixels.shape[1], pixels.shape[0], pixels.shape[2])
        info_str = "{}  - Sampling step is {}.\n".format(info_str, step)
        info_str = "{}  - Radius of {} pixels, {} rings and {} histograms " \
                   "with {} orientations.\n".format(
                   info_str, radius, rings, histograms, orientations)
        if not normalization == 'off':
            info_str = "{}  - Using {} normalization.\n".format(info_str,
                                                                normalization)
        else:
            info_str = "{}  - No normalization emplyed.\n".format(info_str)
        info_str = "{}Output image size {}W x {}H x {}.".format(
            info_str, daisy_descriptor.shape[1], daisy_descriptor.shape[0],
            daisy_descriptor.shape[2])
        print(info_str)

    return daisy_descriptor


# TODO: Needs fixing ...
@winitfeature
def lbp(pixels, radius=None, samples=None, mapping_type='riu2',
        window_step_vertical=1, window_step_horizontal=1,
        window_step_unit='pixels', padding=True, verbose=False,
        skip_checks=False):
    r"""
    Computes a 2-dimensional LBP features image with N*C number of channels,
    where N is the number of channels of the original image and C is the number
    of radius/samples values combinations that are used in the LBP computation.

    Parameters
    ----------
    pixels :  `ndarray`
        The pixel data for the image, where the last axis represents the
        number of channels.

    radius : `int` or `list` of `int`
        It defines the radius of the circle (or circles) at which the sampling
        points will be extracted. The radius (or radii) values must be greater
        than zero. There must be a radius value for each samples value, thus
        they both need to have the same length.

        Default: None = [1, 2, 3, 4]

    samples : `int` or `list` of `int`
        It defines the number of sampling points that will be extracted at each
        circle. The samples value (or values) must be greater than zero. There
        must be a samples value for each radius value, thus they both need to
        have the same length.

        Default: None = [8, 8, 8, 8]

    mapping_type : ``'u2'`` or ``'ri'`` or ``'riu2'`` or ``'none'``
        It defines the mapping type of the LBP codes. Select 'u2' for uniform-2
        mapping, 'ri' for rotation-invariant mapping, 'riu2' for uniform-2 and
        rotation-invariant mapping and 'none' to use no mapping nd only the
        decimal values instead.

    window_step_vertical : float
        Defines the vertical step by which the window in the
        ImageWindowIterator is moved, thus it controls the features density.
        The metric unit is defined by window_step_unit.

    window_step_horizontal : float
        Defines the horizontal step by which the window in the
        ImageWindowIterator is moved, thus it controls the features density.
        The metric unit is defined by window_step_unit.

    window_step_unit : ``'pixels'`` or ``'window'``
        Defines the metric unit of the window_step_vertical and
        window_step_horizontal parameters for the ImageWindowIterator object.

    padding : bool
        Enables/disables padding for the close-to-boundary windows in the
        ImageWindowIterator object. When padding is enabled, the
        out-of-boundary pixels are set to zero.

    verbose : `bool`, optional
        Flag to print LBP related information.

    skip_checks : `bool`, optional
        If True
    Raises
    -------
    ValueError
        Radius and samples must both be either integers or lists
    ValueError
        Radius and samples must have the same length
    ValueError
        Radius must be > 0
    ValueError
        Radii must be > 0
    ValueError
        Samples must be > 0
    ValueError
        Mapping type must be u2, ri, riu2 or none
    ValueError
        Horizontal window step must be > 0
    ValueError
        Vertical window step must be > 0
    ValueError
        Window step unit must be either pixels or window
    """
    if radius is None:
        radius = range(1, 5)
    if samples is None:
        samples = [8]*4

    # TODO: This is a temporal fix
    # flip axis
    pixels = np.rollaxis(pixels, 0, len(pixels.shape))

    if not skip_checks:
        # Check parameters
        if ((isinstance(radius, int) and isinstance(samples, list)) or
                (isinstance(radius, list) and isinstance(samples, int))):
            raise ValueError("Radius and samples must both be either integers "
                             "or lists")
        elif isinstance(radius, list) and isinstance(samples, list):
            if len(radius) != len(samples):
                raise ValueError("Radius and samples must have the same "
                                 "length")

        if isinstance(radius, int) and radius < 1:
            raise ValueError("Radius must be > 0")
        elif isinstance(radius, list) and sum(r < 1 for r in radius) > 0:
            raise ValueError("Radii must be > 0")

        if isinstance(samples, int) and samples < 1:
            raise ValueError("Samples must be > 0")
        elif isinstance(samples, list) and sum(s < 1 for s in samples) > 0:
            raise ValueError("Samples must be > 0")

        if mapping_type not in ['u2', 'ri', 'riu2', 'none']:
            raise ValueError("Mapping type must be u2, ri, riu2 or "
                             "none")

        if window_step_horizontal <= 0:
            raise ValueError("Horizontal window step must be > 0")

        if window_step_vertical <= 0:
            raise ValueError("Vertical window step must be > 0")

        if window_step_unit not in ['pixels', 'window']:
            raise ValueError("Window step unit must be either pixels or "
                             "window")

    # Correct input image_data
    pixels = np.asfortranarray(pixels)

    # Parse options
    radius = np.asfortranarray(radius)
    samples = np.asfortranarray(samples)
    window_height = np.uint32(2 * radius.max() + 1)
    window_width = window_height
    if window_step_unit == 'window':
        window_step_vertical = np.uint32(window_step_vertical * window_height)
        window_step_horizontal = np.uint32(window_step_horizontal *
                                           window_width)
    if mapping_type == 'u2':
        mapping_type = 1
    elif mapping_type == 'ri':
        mapping_type = 2
    elif mapping_type == 'riu2':
        mapping_type = 3
    else:
        mapping_type = 0

    # Create iterator object
    iterator = WindowIterator(pixels, window_height, window_width,
                              window_step_horizontal, window_step_vertical,
                              padding)

    # Print iterator's info
    if verbose:
        print(iterator)

    # Compute LBP
    lbp_descriptor = iterator.LBP(radius, samples, mapping_type, verbose)

    # TODO: This is a temporal fix
    # flip axis
    lbp_descriptor = WindowIteratorResult(
        np.ascontiguousarray(np.rollaxis(lbp_descriptor.pixels, -1)),
        lbp_descriptor.centres)
    return lbp_descriptor

    # # store parameters
    # lbp_image.lbp_parameters = {'radius': radius, 'samples': samples,
    #                             'mapping_type': mapping_type,
    #
    #                             'window_step_vertical':
    #                                 window_step_vertical,
    #                             'window_step_horizontal':
    #                                 window_step_horizontal,
    #                             'window_step_unit': window_step_unit,
    #                             'padding': padding,
    #
    #                             'original_image_height':
    #                                 self._image.pixels.shape[0],
    #                             'original_image_width':
    #                                 self._image.pixels.shape[1],
    #                             'original_image_channels':
    #                                 self._image.pixels.shape[2]}


@ndfeature
def no_op(image_data):
    r"""
    A no operation feature - does nothing but return a copy of the pixels
    passed in.
    """
    return image_data.copy()
