#========================================================================
# Copyright 2019 Science Technology Facilities Council
# Copyright 2019 University of Manchester
#
# This work is part of the Core Imaging Library developed by Science Technology
# Facilities Council and University of Manchester
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0.txt
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#=========================================================================
""" 

Total Generalised Variation (TGV) Denoising using PDHG algorithm:


Problem:     min_{x} \alpha * ||\nabla x - w||_{2,1} +
                     \beta *  || E w ||_{2,1} +
                     fidelity

            where fidelity can be as follows depending on the noise characteristics
            of the data:
                * Norm2Squared     \frac{1}{2} * || x - g ||_{2}^{2}
                * KullbackLeibler  \int u - g * log(u) + Id_{u>0}
                * L1Norm           ||u - g||_{1}

             \alpha: Regularization parameter
             \beta:  Regularization parameter
             
             \nabla: Gradient operator 
              E: Symmetrized Gradient operator
             
             g: Noisy Data with Salt & Pepper Noise
                          
             Method = 0 ( PDHG - split ) :  K = [ \nabla, - Identity
                                                  ZeroOperator, E 
                                                  Identity, ZeroOperator]
                          
                                                                    
             Method = 1 (PDHG - explicit ):  K = [ \nabla, - Identity
                                                  ZeroOperator, E ] 
                                                                
"""

from ccpi.framework import ImageData, ImageGeometry

import numpy as np 
import numpy                          
import matplotlib.pyplot as plt

from ccpi.optimisation.algorithms import PDHG

from ccpi.optimisation.operators import BlockOperator, Identity, \
                        Gradient, SymmetrizedGradient, ZeroOperator
from ccpi.optimisation.functions import ZeroFunction, L1Norm, \
                      MixedL21Norm, BlockFunction, KullbackLeibler, L2NormSquared
import sys
if int(numpy.version.version.split('.')[1]) > 12:
    from skimage.util import random_noise
else:
    from demoutil import random_noise



# user supplied input
if len(sys.argv) > 1:
    which_noise = int(sys.argv[1])
else:
    which_noise = 0
print ("Applying {} noise")

if len(sys.argv) > 2:
    method = sys.argv[2]
else:
    method = '1'
print ("method ", method)
# Create phantom for TGV SaltPepper denoising

N = 100

x1 = np.linspace(0, int(N/2), N)
x2 = np.linspace(int(N/2), 0., N)
xv, yv = np.meshgrid(x1, x2)

xv[int(N/4):int(3*N/4)-1, int(N/4):int(3*N/4)-1] = yv[int(N/4):int(3*N/4)-1, int(N/4):int(3*N/4)-1].T

#data = xv

ig = ImageGeometry(voxel_num_x = N, voxel_num_y = N)
data = ig.allocate()
data.fill(xv/xv.max())
ag = ig

# Create noisy data. 
# Apply Salt & Pepper noise
# gaussian
# poisson
noises = ['gaussian', 'poisson', 's&p']
noise = noises[which_noise]
if noise == 's&p':
    n1 = random_noise(data.as_array(), mode = noise, salt_vs_pepper = 0.9, amount=0.2, seed=10)
elif noise == 'poisson':
    n1 = random_noise(data.as_array(), mode = noise, seed = 10)
elif noise == 'gaussian':
    n1 = random_noise(data.as_array(), mode = noise, seed = 10)
else:
    raise ValueError('Unsupported Noise ', noise)
noisy_data = ImageData(n1)

# Show Ground Truth and Noisy Data
plt.figure(figsize=(10,5))
plt.subplot(1,2,1)
plt.imshow(data.as_array())
plt.title('Ground Truth')
plt.colorbar()
plt.subplot(1,2,2)
plt.imshow(noisy_data.as_array())
plt.title('Noisy Data')
plt.colorbar()
plt.show()

# Regularisation Parameters
if noise == 's&p':
    alpha = 0.8
elif noise == 'poisson':
    alpha = .1
elif noise == 'gaussian':
    alpha = .3

beta = numpy.sqrt(2)* alpha

# fidelity
if noise == 's&p':
    f3 = L1Norm(b=noisy_data)
elif noise == 'poisson':
    f3 = KullbackLeibler(noisy_data)
elif noise == 'gaussian':
    f3 = L2NormSquared(b=noisy_data)

if method == '0':
    
    # Create operators
    op11 = Gradient(ig)
    op12 = Identity(op11.range_geometry())
    
    op22 = SymmetrizedGradient(op11.domain_geometry())    
    op21 = ZeroOperator(ig, op22.range_geometry())
        
    op31 = Identity(ig, ag)
    op32 = ZeroOperator(op22.domain_geometry(), ag)
    
    operator = BlockOperator(op11, -1*op12, op21, op22, op31, op32, shape=(3,2) ) 
        
    f1 = alpha * MixedL21Norm()
    f2 = beta * MixedL21Norm() 
    # f3 depends on the noise characteristics
    
    f = BlockFunction(f1, f2, f3)         
    g = ZeroFunction()
        
else:
    
    # Create operators
    op11 = Gradient(ig)
    op12 = Identity(op11.range_geometry())
    op22 = SymmetrizedGradient(op11.domain_geometry())    
    op21 = ZeroOperator(ig, op22.range_geometry())    
    
    operator = BlockOperator(op11, -1*op12, op21, op22, shape=(2,2) )      
    
    f1 = alpha * MixedL21Norm()
    f2 = beta * MixedL21Norm()     
    
    f = BlockFunction(f1, f2)         
    g = BlockFunction(f3, ZeroFunction())
     
## Compute operator Norm
normK = operator.norm()
#
# Primal & dual stepsizes
sigma = 1
tau = 1/(sigma*normK**2)


# Setup and run the PDHG algorithm
pdhg = PDHG(f=f,g=g,operator=operator, tau=tau, sigma=sigma)
pdhg.max_iteration = 2000
pdhg.update_objective_interval = 200
pdhg.run(2000, verbose = True)

#%%
plt.figure(figsize=(20,5))
plt.subplot(1,4,1)
plt.imshow(data.as_array())
plt.title('Ground Truth')
plt.colorbar()
plt.subplot(1,4,2)
plt.imshow(noisy_data.as_array())
plt.title('Noisy Data')
plt.colorbar()
plt.subplot(1,4,3)
plt.imshow(pdhg.get_output()[0].as_array())
plt.title('TGV Reconstruction')
plt.colorbar()
plt.subplot(1,4,4)
plt.plot(np.linspace(0,N,N), data.as_array()[int(N/2),:], label = 'GTruth')
plt.plot(np.linspace(0,N,N), pdhg.get_output()[0].as_array()[int(N/2),:], label = 'TGV reconstruction')
plt.legend()
plt.title('Middle Line Profiles')
plt.show()

