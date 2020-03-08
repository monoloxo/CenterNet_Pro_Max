#!/usr/bin/python3
# -*- coding:utf-8 -*-
import math

import torch.nn as nn
from alfred.utils.log import logger

"""
normal deconv without dcn

"""


class DeconvLayer(nn.Module):
    def __init__(
        self, in_planes,
        out_planes, deconv_kernel,
        deconv_stride=2, deconv_pad=1,
        deconv_out_pad=0
    ):
        super(DeconvLayer, self).__init__()
        # if modulate_deform:
        #     self.dcn = ModulatedDeformConvWithOff(
        #         in_planes, out_planes,
        #         kernel_size=3, deformable_groups=1,
        #     )
        # else:
        #     self.dcn = DeformConvWithOff(
        #         in_planes, out_planes,
        #         kernel_size=3, deformable_groups=1,
        #     )
        self.conv = nn.Conv2d(
            in_planes, out_planes, kernel_size=3
        )

        self.dcn_bn = nn.BatchNorm2d(out_planes)
        self.up_sample = nn.ConvTranspose2d(
            in_channels=out_planes,
            out_channels=out_planes,
            kernel_size=deconv_kernel,
            stride=deconv_stride, padding=deconv_pad,
            output_padding=deconv_out_pad,
            bias=False,
        )
        self._deconv_init()
        self.up_bn = nn.BatchNorm2d(out_planes)
        self.relu = nn.ReLU()

    def forward(self, x):
        logger.info('in x shpe: {}'.format(x.shape))
        x = self.conv(x)
        logger.info('dcn out shpe: {}'.format(x.shape))
        # should be 256, 16, 16 | 128, 32, 32| 64, 64, 64
        x = self.dcn_bn(x)
        logger.info('dcn_bn out shpe: {}'.format(x.shape))
        x = self.relu(x)
        x = self.up_sample(x)
        x = self.up_bn(x)
        x = self.relu(x)
        return x

    def _deconv_init(self):
        w = self.up_sample.weight.data
        f = math.ceil(w.size(2) / 2)
        c = (2 * f - 1 - f % 2) / (2. * f)
        for i in range(w.size(2)):
            for j in range(w.size(3)):
                w[0, 0, i, j] = \
                    (1 - math.fabs(i / f - c)) * (1 - math.fabs(j / f - c))
        for c in range(1, w.size(0)):
            w[c, 0, :, :] = w[0, 0, :, :]


class CenternetDeconv(nn.Module):
    """
    The head used in CenterNet for object classification and box regression.
    It has three subnet, with a common structure but separate parameters.
    """
    def __init__(self, cfg):
        super(CenternetDeconv, self).__init__()
        # modify into config
        channels = cfg.MODEL.CENTERNET.DECONV_CHANNEL
        deconv_kernel = cfg.MODEL.CENTERNET.DECONV_KERNEL
        self.deconv1 = DeconvLayer(
            channels[0], channels[1],
            deconv_kernel=deconv_kernel[0],
        )
        self.deconv2 = DeconvLayer(
            channels[1], channels[2],
            deconv_kernel=deconv_kernel[1],
        )
        self.deconv3 = DeconvLayer(
            channels[2], channels[3],
            deconv_kernel=deconv_kernel[2],
        )

    def forward(self, x):
        x = self.deconv1(x)
        x = self.deconv2(x)
        x = self.deconv3(x)
        return x