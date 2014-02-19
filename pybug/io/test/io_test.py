import pybug.io as pio
from pybug.shape import TriMesh
from numpy.testing import assert_allclose
import numpy as np

# ground truth bunny landmarks
bunny_l_eye = np.array([[-0.09009447,  0.13760692,  0.02303147]])
bunny_r_eye = np.array([[-0.06041192,  0.13871727,  0.03462752]])
bunny_nose = np.array([[-0.07949748,  0.12401747,  0.05170817]])
bunny_mouth = np.array([[-0.08876467,  0.11684129,  0.04538456],
                        [-0.08044379,  0.11318078,  0.04642309],
                        [-0.07329408,  0.11268603,  0.04844998],
                        [-0.0670796 ,  0.11644761,  0.0498054 ]])


def test_import_asset_bunny():
    mesh = pio.import_builtin_asset('bunny.obj')
    assert(isinstance(mesh, TriMesh))


def test_json_landmarks_bunny():
    mesh = pio.import_builtin_asset('bunny.obj')
    assert('JSON' in mesh.landmarks.group_labels)
    lms = mesh.landmarks['JSON']
    labels = {'r_eye', 'mouth', 'nose', 'l_eye'}
    assert(len(labels - set(lms.labels)) == 0)
    assert_allclose(lms['l_eye'].lms.points, bunny_l_eye, atol=1e-7)
    assert_allclose(lms['r_eye'].lms.points, bunny_r_eye, atol=1e-7)
    assert_allclose(lms['nose'].lms.points, bunny_nose, atol=1e-7)
    assert_allclose(lms['mouth'].lms.points, bunny_mouth, atol=1e-7)
