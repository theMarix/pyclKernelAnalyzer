#!/usr/bin/env python
# coding=utf8

# This file is part of pyclKernelAnalyzer.
#
# pyclKernelAnalyzer is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# pyclKernelAnalyzer is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with pyclKernelAnalyzer.  If not, see <http://www.gnu.org/licenses/>.
#
# (c) 2012 Matthias Bach <bach@compeng.uni-frankfurt.de>

import pyopencl as cl
import optparse
import os
import re

class OutputWriter:

	def __init__(self, csv):
		self.csv = csv
		print 'Device Version, Driver Version, Kernel Name, GPRs, Scratch Registers, Local Memory (Bytes)'


	def writeLine(self, device, kernel, GPRs, scratchRegs, staticMem):
		if self.csv:
			format = '{1.function_name},{2},{3},{4},{0.version},{0.driver_version}'
		else:
			format = '{1.function_name}\t{2}\t{3}\t{4}\t{0.version}\t{0.driver_version}'
		print format.format(device, kernel, GPRs, scratchRegs, staticMem)

def file2string(filename):
	f = open(filename, 'r')
	fstr = ''.join(f.readlines())
	return fstr

if __name__ == '__main__':
	parser = optparse.OptionParser(description='Figure out resource usage for all kernels in the given source files.', usage='analyze.py FILES...')
	parser.add_option('-d', '--device', type=int, metavar='I', help='The device for which to compile the kernels')
	parser.add_option('--csv', action='store_true', default=False, help='Output results as CSV')

	(args, files) = parser.parse_args()

	if len(files) == 0:
		print 'You must specify at least one source file!'
		exit(-1)

	writer = OutputWriter(args.csv)

	# before initializing opencl make sure the AMD compiler will dump the source
	os.environ['GPU_DUMP_DEVICE_KERNEL'] = '3'

	if args.device != None: # compare with None to make device = 0 truthy
		platforms = cl.get_platforms()
		if len(platforms) > 1:
			raise Exception('Found more then one platform, giving up.')
		platform = platforms[0]
		properties = [(cl.context_properties.PLATFORM, platform)]
		devices = [platform.get_devices()[args.device]]
		ctx = cl.Context(devices, properties)
	else:
		ctx = cl.create_some_context()

	device = ctx.devices[0]

	source = ''.join(map(file2string, files))

	prg = cl.Program(ctx, source)
	prg.build()

	try:
		kernels = prg.all_kernels()
	except AttributeError:
		# crude logic to find kernels, won't work in all cases
		kernels = map(lambda name: getattr(prg, name), re.findall(r"^\s*__kernel\s+void\s+(\w+)\(", source, re.MULTILINE));

	for kernel in kernels:
		isaFileName = kernel.function_name + '_' + device.name + '.isa'

		isaFile = file2string(isaFileName)

		scratchRegs = int(re.search(r"^MaxScratchRegsNeeded\s*=\s*(\d*)\s*$", isaFile, re.MULTILINE).group(1))
		GPRs = int(re.search(r"^SQ_PGM_RESOURCES:NUM_GPRS\s*=\s*(\d*)\s*$", isaFile, re.MULTILINE).group(1))
		static = int(re.search(r"^SQ_LDS_ALLOC:SIZE\s*=\s*(0x\d*)\s*$", isaFile, re.MULTILINE).group(1), 0) * 4 # value in file is in units of floats

		writer.writeLine(device, kernel, GPRs, scratchRegs, static)

