#!/usr/bin/env /usr/bin/python



from gnuradio import gr, atsc, blocks, analog, digital, filter, uhd
from gnuradio.filter import firdes
from grc_gnuradio import blks2 as grc_blks2
import sys, os
import osmosdr

def main(args):
    nargs = len(args)
    if nargs == 1:
        port    = int(args[0])
        outfile = None
    elif nargs == 2:
        port    = int(args[0])
        outfile  = args[1]
    else:
        sys.stderr.write("Usage: atsc-blade.py port [output_file]\n");
        sys.exit(1)

    symbol_rate = 4500000.0 / 286 * 684
    pilot_freq = 309441
    center_freq = 441000000
    tx_gain = 83 # max 89.5

    tb = gr.top_block()

    out = uhd.usrp_sink(
        	device_addr="recv_frame_size=65536,num_recv_frames=128,send_frame_size=65536,num_send_frames=128,master_clock_rate=" + str(symbol_rate*4),
        	stream_args=uhd.stream_args(
        		cpu_format="fc32",
        		otw_format="sc16",
        		channels=range(1),
        	),
        )
    out.set_samp_rate(symbol_rate)
    out.set_center_freq(center_freq, 0)
    out.set_gain(tx_gain, 0)

    #src = blocks.udp_source(gr.sizeof_char*1, "127.0.0.1", port, 18800, True)
    src = grc_blks2.tcp_source(gr.sizeof_char*1, "127.0.0.1", port, True)

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
    rrc = filter.fft_filter_ccc(1, firdes.root_raised_cosine(0.1, symbol_rate, symbol_rate/2, 0.1152, 100))

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
