# -*- coding: utf-8 -*-
"""
Created on Fri Aug 28 09:33:36 2020

@author: huijianpzh
"""

import math
import copy

import torch
import torch.nn as nn

import torch.nn.functional as F


class DUC(nn.Module):
    def __init__(self, inplanes, planes, upscale_factor=2):
        super(DUC, self).__init__()
        self.relu = nn.ReLU()
        self.conv = nn.Conv2d(inplanes, planes, kernel_size=3,
                              padding=1)
        self.bn = nn.BatchNorm2d(planes)
        self.pixel_shuffle = nn.PixelShuffle(upscale_factor)

    def forward(self, x):
        x = self.conv(x)
        x = self.bn(x)
        x = self.relu(x)
        x = self.pixel_shuffle(x)
        return x

def conv1x1(in_chs,out_chs,
            stride=1,pad=0,
            bias=False):
    "1x1 convolution"
    return nn.Conv2d(in_channels=in_chs,out_channels=out_chs,kernel_size=1,
                     stride=stride,padding=pad,bias=bias)

def upsample(scale_factor,mode="bilinear",align_corners=False):
    return nn.Upsample(scale_factor=scale_factor,mode=mode,align_corners=align_corners)

def conv3x3(in_chs,out_chs,
            stride=1,pad=1,
            bias=False):
    "3x3 convolution with padding"
    return nn.Conv2d(in_channels=in_chs,out_channels=out_chs, 
                     kernel_size=3,
                     stride=stride,padding=pad,bias=bias)


def CONV_BN(in_chs,out_chs,
            kernel=3,stride=1,
            dilation=1,pad=1,
            bias=False):
    op = nn.Sequential(nn.Conv2d(in_chhannels=in_chs,out_channels=out_chs,
                                 kernel_size=kernel,stride=stride,
                                 dilation=dilation,padding=pad,bias=bias),
                       nn.BatchNorm2d(out_chs),
                       )
    return op
    

def CONV_BN_AC(in_chs,out_chs,
            kernel=3,stride=1,
            dilation=1,pad=1,
            bias=False):
    op = nn.Sequential(nn.Conv2d(in_channels=in_chs,out_channels=out_chs,
                                 kernel_size=kernel,stride=stride,
                                 dilation=dilation,padding=pad,bias=bias),
                       nn.BatchNorm2d(out_chs),
                       nn.ReLU(),
                       )
    return op

def UPCONV_BN_AC(in_chs,out_chs,
                 kernel=2,stride=2,
                 dilation=1,
                 pad=0,output_pad=0,
                 bias=False):
    op = nn.Sequential(nn.ConvTranspose2d(in_channels=in_chs,out_channels=out_chs,
                                          kernel_size=kernel,stride=stride,
                                          padding=pad,output_padding=output_pad,
                                          dilation=dilation,bias=bias),
                       nn.BatchNorm2d(out_chs),
                       nn.ReLU()
        )
    return op

"""
dilation will be only 1.
It not easy to adjust the dilate rate within BasicBlock.
Notice: Though We provider the dilation here, it will not work.
"""
class BasicBlock(nn.Module):
    expansion = 1
    def __init__(self,inplanes,planes,stride=1,downsample=None,bias=False,
                 dilation=1,extra_dilation=1):
        super(BasicBlock,self).__init__()
        
        self.conv1 = nn.Conv2d(inplanes,planes,
                               kernel_size=3,stride=stride,
                               dilation=dilation,padding=dilation,
                               bias=bias)
        
        self.bn1 = nn.BatchNorm2d(planes)
        self.relu = nn.ReLU(inplace=True)
        
        
        self.conv2 = nn.Conv2d(planes,planes,
                               kernel_size=3,stride=1,
                               dilation=extra_dilation,padding=extra_dilation,
                               bias=bias)
        self.bn2 = nn.BatchNorm2d(planes)
        
        self.downsample=downsample
        self.stride=stride
    
    def forward(self,input_tensor):
        
        identify = input_tensor
        
        x = self.conv1(input_tensor)
        x = self.bn1(x)
        x = self.relu(x)
        
        x = self.conv2(x)
        x = self.bn2(x)
        
        if self.downsample is not None:
            identify = self.downsample(input_tensor)
        
        output_tensor = self.relu( x + identify )
        
        return output_tensor
"""
The Bottleneck is different from BasicBlock for the dilation can be set directly.
"""
class Bottleneck(nn.Module):
    expansion = 4
    def __init__(self,inplanes,planes,stride=1,downsample=None,dilation=1,bias=False):
        super(Bottleneck,self).__init__()
        
        # 1x1 conv stride
        self.conv1 = nn.Conv2d(inplanes,planes,
                               kernel_size=1,
                               stride=stride,
                               bias=bias)
        self.bn1 = nn.BatchNorm2d(planes)
        
        # 3x3 conv dilation
        self.conv2 = nn.Conv2d(planes,planes,
                               kernel_size=3,
                               dilation=dilation,padding=dilation,
                               bias=bias)
        self.bn2 = nn.BatchNorm2d(planes)
        
        self.conv3 = nn.Conv2d(planes,planes * 4,
                               kernel_size=1,bias=bias)
        self.bn3 = nn.BatchNorm2d(planes*4)
        
        self.relu = nn.ReLU(inplace = True)
        
        self.downsample = downsample
        self.stride=stride
    def forward(self,input_tensor):
        
        identify = input_tensor
        
        x = self.conv1(input_tensor)
        x = self.bn1(x)
        x = self.relu(x)
        
        x = self.conv2(x)
        x = self.bn2(x)
        x = self.relu(x)
        
        x = self.conv3(x)
        x = self.bn3(x)
        
        if self.downsample is not None:
            identify = self.downsample(input_tensor)
          
        output_tensor = self.relu(x + identify)
        return output_tensor
"""

------ Effecient FCN ------

"""

class Softmax2d(nn.Module):
    def __init__(self):
        super(Softmax2d,self).__init__()
        return
    def forward(self,input_tensor):
        # this fcn is for 4d tensor
        assert len(input_tensor.size())==4
        
        bs,c,h,w = input_tensor.size()
        x = input_tensor.view((bs,c,-1))
        x = x.contiguous()
        x = F.softmax(x,dim=2)
        x = x.view((bs,c,h,w))
        output_ = x.contiguous()
        
        return output_

class EffecientFCN(nn.Module):
    def __init__(self,in_chs,out_chs, num_of_sp_weight=64,
                 block=BasicBlock,layers=[3,4,6,3]):
        self.inplanes = 64
        super(EffecientFCN,self).__init__()
        
        self.num_of_sp_weight = num_of_sp_weight
        
        # ------ encoder part ------
        self.conv1 = nn.Conv2d(3, 64, kernel_size=7, stride=2, padding=3,
                               bias=False)
        self.bn = nn.BatchNorm2d(64)
        self.relu = nn.ReLU(inplace=True)
        self.maxpool = nn.MaxPool2d(kernel_size=3, stride=2, padding=1, ceil_mode=False) # change
        self.layer1 = self._make_layer(block, 64, layers[0])
        self.layer2 = self._make_layer(block, 128, layers[1], stride=2)
        self.layer3 = self._make_layer(block, 256, layers[2], stride=2) 
        self.layer4 = self._make_layer(block, 512, layers[3], stride=2) 
        
        expansion = block.expansion
        
        # ------ multi-scale feature fusion ------
        # reduce the dimension first
        bn_ = False
        if bn_:
            self.os_32_r_conv = CONV_BN_AC(in_chs=expansion*512,out_chs=512,kernel=1,stride=1,dilation=1,pad=0,bias=False)
            self.os_16_r_conv = CONV_BN_AC(in_chs=expansion*256,out_chs=512,kernel=1,stride=1,dilation=1,pad=0,bias=False)
            self.os_8_r_conv = CONV_BN_AC(in_chs=expansion**128,out_chs=512,kernel=1,stride=1,dilation=1,pad=0,bias=False)
        else:
            self.os_32_r_conv = conv1x1(in_chs=expansion*512,out_chs=512,stride=1,pad=0,bias=False)
            self.os_16_r_conv = conv1x1(in_chs=expansion*256,out_chs=256,stride=1,pad=0,bias=False)
            self.os_8_r_conv = conv1x1(in_chs=expansion*128,out_chs=128,stride=1,pad=0,bias=False)
        
        # bilinear
        # down
        self.downsample2 = upsample(scale_factor=0.5,mode="bilinear",align_corners=False)
        self.downsample4 = upsample(scale_factor=0.25,mode="bilinear",align_corners=False)
        
        # up
        self.upsample2 = upsample(scale_factor=2,mode="bilinear",align_corners=False)
        self.upsamlpe4 = upsample(scale_factor=4,mode="bilinear",align_corners=False)
        
        # ------ generate holistic codeword and codeword base map ------ 
        bn_ = False
        if bn_:
            # codewords base map
            self.codewords_conv=CONV_BN_AC(in_chs=1536,out_chs=1024,kernel=1,stride=1,dilation=1,pad=0,bias=False)
            # spatial weight map
            self.sp_weight_conv=CONV_BN_AC(in_chs=1536,out_chs=1024,kernel=1,stride=1,dilation=1,pad=0,bias=False)
        else:
            self.codewords_conv =  conv1x1(in_chs=3*512,out_chs=1024,stride=1,pad=0,bias=False)
            self.sp_weight_conv = conv1x1(in_chs=3*512,out_chs=self.num_of_sp_weight,stride=1,pad=0,bias=False)
        
        self.avg_pool = nn.AdaptiveAvgPool2d((1,1))
        
        # softmax function for spatial weight map
        self.spatial_softmax = Softmax2d()
        
        # ------ generate codeword assembly ------
        bn_ = False
        if bn_:
            self.assembly_coefficient_cov = CONV_BN_AC(in_chs=1536,out_chs=1024,kernel=1,stride=1,dilation=1,pad=0,bias=False)
        else:
            self.assembly_coefficient_cov = conv1x1(in_chs=3*512,out_chs=1024,stride=1,pad=0,bias=False)
        
        bn_ = False
        if bn_:
            self.guidance_process_conv = CONV_BN_AC(in_chs=1024,out_chs=self.num_of_sp_weight,kernel=1,stride=1,dilation=1,pad=0,bias=False)
        else:
            self.guidance_process_conv = conv1x1(in_chs=1024,out_chs=self.num_of_sp_weight,stride=1,pad=0,bias=False)
        
        
        self.final_upconv = nn.Sequential(
            CONV_BN_AC(in_chs=2048, out_chs=1024,kernel=1,pad=0),
            DUC(inplanes=1024, planes=64*64,upscale_factor=8),
            CONV_BN_AC(in_chs=64,out_chs=64),
            CONV_BN_AC(in_chs=64,out_chs=64)
            )
        
        self.classifier = nn.Conv2d(in_channels=64, 
                                    out_channels=out_chs, kernel_size=1)
        
        
        # ------ initialize the weights ------
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                n = m.kernel_size[0] * m.kernel_size[1] * m.out_channels
                m.weight.data.normal_(0, math.sqrt(2. / n))
            elif isinstance(m, nn.BatchNorm2d):
                m.weight.data.fill_(1)
                m.bias.data.zero_()
        
    def _make_layer(self,block,planes,blocks,
                    stride=1,bias=False):
        downsample = None
        if stride != 1 or self.inplanes != planes*block.expansion:
            # for downsample, dilation makes no difference.
            downsample = nn.Sequential(
                nn.Conv2d(self.inplanes,planes*block.expansion,
                          kernel_size=1,stride=stride,
                          bias=bias),
                nn.BatchNorm2d(planes*block.expansion)
                )
        layers = []
        layers.append(block(self.inplanes,planes,stride,downsample))
        self.inplanes = planes * block.expansion
        for i in range(1,blocks):
            layers.append(block(self.inplanes,planes))
        return nn.Sequential(*layers)
    
    
    def forward(self,input_tensor):
        
        # ------ get features ------
        x = self.conv1(input_tensor)
        x = self.bn(x)
        x = self.relu(x)
        x = self.maxpool(x)
        
        x = self.layer1(x)
        os_8_ = self.layer2(x)
        os_16_ = self.layer3(os_8_)
        os_32_ = self.layer4(os_16_)
        
        # ------ multi-scale feature fusion ------
        # up & down sample
        os_8_down_ = self.downsample4(os_8_)
        os_16_down_ = self.downsample2(os_16_)
        
        os_32_up_ = self.upsamlpe4(os_32_)
        os_16_up_ = self.upsample2(os_16_)
        # fuse
        os_l_ = torch.cat([os_8_,os_16_up_,os_32_up_])
        os_s_ = torch.cat([os_8_down_,os_16_down_,os_32_])
        
        # ------ generate holistic codeword and codeword base map ------ 
        codewords_base_map = self.codewords_conv(os_s_) # [bs,1024,h/32,w/32]
        sp_weight = self.sp_weight_conv(os_s_) # [bs,n,h/32,w/32]
        
        bs,chs,h_32_,w_32_ = sp_weight.size()
        
        new_sp_weight = sp_weight.expand((bs,self.num_of_sp_weight,chs,h_32_,w_32_))
        new_codewords_base_map = codewords_base_map.expand(bs,self.num_of_sp_weight,chs,h_32_,w_32_)
        # semantic_codebook [bs,num_of_sp_weight,1024]
        semantic_codebook = torch.mul(new_sp_weight,new_codewords_base_map).sum(dim=-1).sum(dim=-1)
        
        global_codeword_info = self.avg_pool(codewords_base_map)
        
        # ------ generate codeword assembly ------
        raw_assembly_coefficient = self.assembly_coefficient_cov(os_l_)
        assembly_coefficient = raw_assembly_coefficient + global_codeword_info  # [bs,1024,h/8,w/8]
        assembly_coefficient = self.guidance_process_conv(assembly_coefficient) # [bs,num_of_sp_weight,h/8,w/8]
        
        # holistically-guided upsample
        # [bs,n,h/8,w/8] -> [bs,n,h/8*w/8]
        _,__,h_8_,w_8_ = assembly_coefficient.size()
        assembly_coefficient = assembly_coefficient.view((bs,self.num_of_sp_weight,-1))
        # change the order -> [bs,h*w/64,n]
        assembly_coefficient = assembly_coefficient.permute(0,2,1).contiguous()
        
        # equation (3) matrix multiply and get a tensor of [bs,h*w/64,1024]
        x = torch.bmm(assembly_coefficient,semantic_codebook)
        # get chs
        _,__,chs = x.size()
        x = x.view((bs,h_8_,w_8_,chs))     
        x = x.permute(0,3,1,2).contiguous() # [bs,1024,h/8,w/8]
        
        x = torch.cat([x,raw_assembly_coefficient],dim=1)
        x = self.final_upconv(x)
        
        output_tensor = self.classifier(x)
        
        return output_tensor
    
if __name__=="__main__":
    print("test4EfficientFCN")