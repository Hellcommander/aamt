// Single compilation unit for the vendored stb_vorbis Ogg Vorbis decoder used by
// the audio generators (AudioFileIO::decodeOggMemory). stb_vorbis is a single-file
// library: including it without STB_VORBIS_HEADER_ONLY emits the implementation.
// No other translation unit of the backend compiles stb_vorbis.
#include "vendor/stb/stb_vorbis.c"
