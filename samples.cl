__kernel void vecAdd(__global float * const restrict out, __global const float * const restrict in1, __global const float * const restrict in2)
{
	const size_t id = get_global_id(0);
	out[id] = in1[id] + in2[id];
}

__kernel void vecMulAdd(__global float * const restrict out, __global const float * const restrict in1, __global const float * const restrict in2,  __global const float * const restrict in3)
{
	const size_t id = get_global_id(0);
	out[id] = in1[id] * in2[id] + in3[id];
}

__kernel void localMem(__global float * const restrict out, __global const float * const restrict in1) {
	__local float buf[128];
	const size_t id = get_global_id(0);
	const size_t lid = get_local_id(0);

	buf[lid] = in1[id];
	out[id] = buf[lid] + buf[(lid+1) % 128];
}
