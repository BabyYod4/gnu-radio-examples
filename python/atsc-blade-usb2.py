#!/usr/bin/env /usr/bin/python



from gnuradio import gr, atsc, blocks, analog, digital, filter
from gnuradio.filter import firdes
from grc_gnuradio import blks2 as grc_blks2
import sys, os
import osmosdr

def main(args):
    nargs = len(args)
    if nargs == 1:
        infile  = args[0]
        outfile = None
    elif nargs == 2:
        infile  = args[0]
        outfile  = args[1]
    else:
        sys.stderr.write("Usage: atsc-blade.py input_file [output_file]\n");
        sys.exit(1)

    symbol_rate = 4500000.0 / 286 * 684
    pilot_freq = 309441
    center_freq = 441000000
    txvga1_gain = -4
    txvga2_gain = 25

    tb = gr.top_block()

    src = blocks.file_source(gr.sizeof_char, infile, True)

    pad = atsc.pad()
    rand = atsc.randomizer()
    rs_enc = atsc.rs_encoder()
    inter = atsc.interleaver()
    trell = atsc.trellis_encoder()
    fsm = atsc.field_sync_mux()

    v2s = blocks.vector_to_stream(gr.sizeof_char, 1024)
    minn = blocks.keep_m_in_n(gr.sizeof_char, 832, 1024, 4)
    c2sym = digital.chunks_to_symbols_bc(([symbol + 1.25 for symbol in [-7,-5,-3,-1,1,3,5,7]]), 1)
    offset = analog.sig_source_c(symbol_rate, analog.GR_COS_WAVE, -3000000 + pilot_freq, 0.9, 0)
    mix = blocks.multiply_vcc(1)
    rrc_taps = firdes.root_raised_cosine(0.1, symbol_rate*2, symbol_rate/2, 0.1152, 200)
    rrc = filter.rational_resampler_ccc(interpolation=2, decimation=3, taps=rrc_taps, fractional_bw=None, )

    out = osmosdr.sink(args="bladerf=0,buffers=128,buflen=32768")
    out.set_sample_rate(symbol_rate * 2 / 3)
    out.set_center_freq(center_freq, 0)
    out.set_freq_corr(0, 0)
    out.set_gain(txvga2_gain, 0)
    out.set_bb_gain(txvga1_gain, 0)
    out.set_bandwidth(6000000, 0)

    tb.connect(src, pad, rand, rs_enc, inter, trell, fsm, v2s, minn, c2sym)
    tb.connect((c2sym, 0), (mix, 0))
    tb.connect((offset, 0), (mix, 1))
    tb.connect(mix, rrc, out)

    if outfile:
        dst = blocks.file_sink(gr.sizeof_gr_complex, outfile)
        tb.connect(rrc, dst)

    tb.run()


if __name__ == '__main__':
    main(sys.argv[1:])
