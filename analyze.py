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

def file2string(filename):
	f = open(filename, 'r')
	fstr = ''.join(f.readlines())
	return fstr

if __name__ == '__main__':
	parser = optparse.OptionParser(description='Figure out resource usage for all kernels in the given source files.', usage='analyze.py FILES...')
	parser.add_option('-d', '--device', type=int, metavar='I', help='The device for which to compile the kernels')
	parser.add_option('--csv', action='store_true', default=False, help='Output results as CSV')
	parser.add_option('--no-header', action='store_true', default=False, help='Dont add column headers to csv output')
	parser.add_option('-p', '--param', dest='build_options', action='append', default=[], help='Build options to be passed to the OpenCL compiler')

	(args, files) = parser.parse_args()

	if len(files) == 0:
		print 'You must specify at least one source file!'
		exit(-1)

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
	prg.build(args.build_options)

	try:
		kernels = prg.all_kernels()
	except AttributeError:
		# crude logic to find kernels, won't work in all cases
		kernels = map(lambda name: getattr(prg, name), re.findall(r"^\s*__kernel\s+void\s+(\w+)\(", source, re.MULTILINE));

	results = []

	for kernel in kernels:
		isaFileName = kernel.function_name + '_' + device.name + '.isa'

		isaFile = file2string(isaFileName)

		scratchRegs = int(re.search(r"^MaxScratchRegsNeeded\s*=\s*(\d*)\s*$", isaFile, re.MULTILINE).group(1))
		GPRs = int(re.search(r"^SQ_PGM_RESOURCES:NUM_GPRS\s*=\s*(\d*)\s*$", isaFile, re.MULTILINE).group(1))
		static = int(re.search(r"^SQ_LDS_ALLOC:SIZE\s*=\s*(0x\d*)\s*$", isaFile, re.MULTILINE).group(1), 0) * 4 # value in file is in units of floats

		results.append((device, kernel, GPRs, scratchRegs, static))



	if args.csv:
		if not args.no_header:
			print 'Kernel Name,GPRs,Scratch Registers,Local Memory (Bytes),Device Version,Driver Version,Build Options'
		format = '{0[1].function_name},{0[2]},{0[3]},{0[4]},{0[0].version},{0[0].driver_version},{1}'
	else:
		maxNameLength = max(len('Kernel Name'), max(map(lambda x: len(x[1].function_name), results)))
		maxVersionLength = max(len('Version'), max(map(lambda x: len(x[0].version), results)))
		maxDriverLength = max(len('Driver Version'), max(map(lambda x: len(x[0].driver_version), results)))
		# we don't print build options in usual output format as they just clutter up the screen
		header = '{0:<' + str(maxNameLength) + '}   GPRs   Scratch Registers   Local Memory (Bytes)   {1:<' + str(maxVersionLength) + '}   {2:<' + str(maxDriverLength) + '}'
		header = header.format('Kernel Name', 'Version', 'Driver Version')
		print header
		print '{0:{fill}<{headerlen}}'.format('', fill='-', headerlen=len(header))
		format = '{0[1].function_name:<' + str(maxNameLength) + '}   {0[2]:>4}   {0[3]:>17}   {0[4]:>20}   {0[0].version:<' + str(maxVersionLength) + '}   {0[0].driver_version:<' + str(maxDriverLength) + '}'

	for line in results:
		print format.format(line,' '.join(args.build_options))
