/* This file is part of Blackbird by lft.
 *
 * The implementation is rather complex, and is probably easier to
 * understand after first studying the playroutine.
 */

#include <err.h>
#include <getopt.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAXTLEN 32
#define MAXSYNC 128

#define NTRACK 256
#define NINS 48
#define NFX 48

struct ext_symbols {
	uint16_t		seg_play;
	uint16_t		seg_init;
	uint16_t		seg_rplay;
	uint16_t		seg_rinit;
	uint16_t		unpackbufs;
	uint16_t		streamstart;
	uint16_t		ins_ad;
	uint16_t		ins_sr;
	uint16_t		ins_wave;
	uint16_t		ins_filt;
	uint16_t		fx_start;
	uint16_t		wavetable;
	uint16_t		filttable;
	uint16_t		fxtable;
	uint8_t			zp_base;
	uint8_t			INS_RESTART;
	uint8_t			INS_RESTART2;
	uint16_t		sidorg;
	uint16_t		metadata;
	uint8_t			fgcol;
	uint8_t			bgcol;
	uint8_t			rastcol;
};

#include "player.h"
#include "rplayer.h"
#include "prghead.h"

struct trackline {
	uint8_t			ins;
	uint8_t			fx;
	uint8_t			note;
};

struct track {
	uint8_t			used;
	uint8_t			length;
	struct trackline	line[MAXTLEN];
};

struct instrument {
	uint8_t			used;
	uint8_t			ad;
	uint8_t			sr;
	uint8_t			h;
	uint8_t			wlength, wloop;
	uint8_t			*wave1, *wave2, *wave3;
	uint8_t			flength, floop;
	uint8_t			*filter1, *filter2, *filter3;
	uint8_t			wstart, fstart, nreloc;
};

struct fx {
	uint8_t			used;
	uint8_t			length, loop;
	uint8_t			*data;
	uint8_t			start, nreloc;
};

struct songline {
	uint8_t			tt[3];
	uint8_t			ref[3];
	uint8_t			length;
};

struct bytebuf {
	uint8_t			*buf;
	int			nalloc;
	int			pos;
};

struct piece {
	uint16_t		cost;
	uint16_t		offset;	// 0 for literal
	uint8_t			length;
	int8_t			transp;
};

struct decodestate {
	struct bytebuf		rledata;
	struct piece		*paths;
	int			rpos, wpos;
	uint8_t			timer;
	int			bytes;	// just for the stats
	int			vnum;
};

struct syncpoint {
	uint8_t			songpos, trackpos;
	uint8_t			flags;
};

#define SPF_LOOP	1
#define SPF_STREAM	2

struct stream {
	char			*filename;
	uint16_t		addr;
};

struct songline *song;
struct track track[NTRACK];
struct instrument ins[NINS];
struct fx fx[NFX];
struct syncpoint syncpoint[MAXSYNC + 1];
struct stream stream[MAXSYNC];
int songlen, songloopflag, songloop;
int verbose = 0;
int nsyncpoint, nstream;
struct bytebuf filtertbl, fxtbl, wavetbl;
#define FILEORG (0x61e0 - 2)
uint8_t header[0x6900 - FILEORG], *moredata;

const char *namechar = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ+-#@*^:;=,./";

enum {
	FMT_SID,
	FMT_PRG,
	FMT_DIST
};

const uint8_t pet2scr[256] = {
	0x20,0x81,0x82,0x83,0x84,0x85,0x86,0x87,0x88,0x89,0x8a,0x8b,0x8c,0x8d,0x8e,0x8f,
	0x90,0x91,0x92,0x93,0x94,0x95,0x96,0x97,0x98,0x99,0x9a,0x9b,0x9c,0x9d,0x9e,0x9f,
	0x20,0x21,0x22,0x23,0x24,0x25,0x26,0x27,0x28,0x29,0x2a,0x2b,0x2c,0x2d,0x2e,0x2f,
	0x30,0x31,0x32,0x33,0x34,0x35,0x36,0x37,0x38,0x39,0x3a,0x3b,0x3c,0x3d,0x3e,0x3f,
	0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x0a,0x0b,0x0c,0x0d,0x0e,0x0f,
	0x10,0x11,0x12,0x13,0x14,0x15,0x16,0x17,0x18,0x19,0x1a,0x1b,0x1c,0x1d,0x1e,0x1f,
	0x40,0x41,0x42,0x43,0x44,0x45,0x46,0x47,0x48,0x49,0x4a,0x4b,0x4c,0x4d,0x4e,0x4f,
	0x50,0x51,0x52,0x53,0x54,0x55,0x56,0x57,0x58,0x59,0x5a,0x5b,0x5c,0x5d,0x5e,0x5f,
	0xc0,0xc1,0xc2,0xc3,0xc4,0xc5,0xc6,0xc7,0xc8,0xc9,0xca,0xcb,0xcc,0xcd,0xce,0xcf,
	0xd0,0xd1,0xd2,0xd3,0xd4,0xd5,0xd6,0xd7,0xd8,0xd9,0xda,0xdb,0xdc,0xdd,0xde,0xdf,
	0x60,0x61,0x62,0x63,0x64,0x65,0x66,0x67,0x68,0x69,0x6a,0x6b,0x6c,0x6d,0x6e,0x6f,
	0x70,0x71,0x72,0x73,0x74,0x75,0x76,0x77,0x78,0x79,0x7a,0x7b,0x7c,0x7d,0x7e,0x7f,
	0x00,0x01,0x02,0x03,0x04,0x05,0x06,0x07,0x08,0x09,0x0a,0x0b,0x0c,0x0d,0x0e,0x0f,
	0x10,0x11,0x12,0x13,0x14,0x15,0x16,0x17,0x18,0x19,0x1a,0x1b,0x1c,0x1d,0x1e,0x1f,
	0x60,0x61,0x62,0x63,0x64,0x65,0x66,0x67,0x68,0x69,0x6a,0x6b,0x6c,0x6d,0x6e,0x6f,
	0x70,0x71,0x72,0x73,0x74,0x75,0x76,0x77,0x78,0x79,0x7a,0x7b,0x7c,0x7d,0x7e,0x5e,
};

uint8_t flipcase(uint8_t c) {
	if(c >= 'a' && c <= 'z') return c - 'a' + 'A';
	if(c >= 'A' && c <= 'Z') return c - 'A' + 'a';
	return c;
}

void loadfile(char *filename) {
	FILE *f;
	uint8_t goodheader[6] = {0xe0, 0x61, 0x62, 0x62, 0x30, 0x30};
	int moresize;
	int i, j, pos, min, wpos = 0, fpos = 0, fxpos = 0;

	f = fopen(filename, "rb");
	if(!f) err(1, "%s", filename);

	if(fread(header, 1, sizeof(header), f) != sizeof(header)) {
		errx(1, "%s: File too short (1, %d)", filename, (int) sizeof(header));
	}
	if(memcmp(header, goodheader, sizeof(goodheader))) {
		errx(1, "%s: Bad file header", filename);
	}
	moresize = (header[6] | (header[7] << 8)) - 0x6900;
	moredata = malloc(moresize);
	if((i = fread(moredata, 1, moresize, f)) != moresize) {
		errx(1, "%s: File too short (2, %d, %d)", filename, moresize, i);
	}
	fclose(f);

	songlen = header[0x61e6 - FILEORG + 0] + 1;
	songloopflag = header[0x61e6 - FILEORG + 1];
	songloop = header[0x61e6 - FILEORG + 2];

	for(i = 0; i < 3 * 32; i++) {
		header[0x61f0 - FILEORG + i] = flipcase(header[0x61f0 - FILEORG + i]);
	}

	for(i = 0; i < 48; i++) {
		ins[i].ad = header[0x6250 - FILEORG + i];
		ins[i].sr = header[0x6280 - FILEORG + i];
		ins[i].h = header[0x62b0 - FILEORG + i];
		ins[i].wlength = header[0x62e0 - FILEORG + i];
		ins[i].wloop = header[0x6310 - FILEORG + i];
		ins[i].flength = header[0x6340 - FILEORG + i];
		ins[i].floop = header[0x6370 - FILEORG + i];
		ins[i].wave1 = &header[0x6400 - FILEORG + wpos];
		ins[i].wave2 = &header[0x6500 - FILEORG + wpos];
		ins[i].wave3 = &header[0x6600 - FILEORG + wpos];
		ins[i].filter1 = &header[0x6700 - FILEORG + fpos];
		ins[i].filter2 = &header[0x6755 - FILEORG + fpos];
		ins[i].filter3 = &header[0x67aa - FILEORG + fpos];
		wpos += ins[i].wlength;
		fpos += ins[i].flength;
		fx[i].length = header[0x63a0 - FILEORG + i];
		fx[i].loop = header[0x63d0 - FILEORG + i];
		fx[i].data = &header[0x6800 - FILEORG + fxpos];
		fxpos += fx[i].length;
	}

	pos = moresize;
	for(i = NTRACK - 1; i >= 0; i--) {
		track[i].length = moredata[--pos];
		for(j = track[i].length - 1; j >= 0; j--) {
			track[i].line[j].note = moredata[--pos];
			track[i].line[j].fx = moredata[--pos];
			track[i].line[j].ins = moredata[--pos];
		}
		for(j = track[i].length; j < MAXTLEN; j++) {
			track[i].line[j].note = 0xff;
			track[i].line[j].fx = 0xff;
			track[i].line[j].ins = 0xff;
		}
	}

	song = malloc(songlen * sizeof(*song));
	for(i = 0; i < songlen; i++) {
		min = 0xff;
		for(j = 0; j < 3; j++) {
			song[i].tt[j] = moredata[i * 6 + 2 * j + 0];
			song[i].ref[j] = moredata[i * 6 + 2 * j + 1];
			if(track[song[i].ref[j]].length
			&& track[song[i].ref[j]].length < min) {
				min = track[song[i].ref[j]].length;
			}
		}
		if(min == 0xff) min = track[0].length;
		song[i].length = min;
	}
}

void putbyte(struct bytebuf *bb, uint8_t b) {
	if(bb->pos >= bb->nalloc) {
		bb->nalloc = (bb->pos * 2) + 16;
		bb->buf = realloc(bb->buf, bb->nalloc);
	}
	bb->buf[bb->pos++] = b;
}

void flushpending(struct bytebuf *bb, uint8_t *pendnote, int *pendwait) {
	int timeleft = *pendwait;

	if(*pendnote != 0xff) {
		putbyte(bb, (*pendnote << 1) | !timeleft);
		if(timeleft) timeleft--;
		*pendnote = 0xff;
	}
	while(timeleft > 16) {
		putbyte(bb, 0xc0);
		timeleft -= 16;
	}
	if(timeleft > 0 && timeleft <= 8) {
		putbyte(bb, 0xc0 - timeleft);
	} else if(timeleft > 8 && timeleft <= 16) {
		putbyte(bb, 0xd0 - timeleft);
	}
	*pendwait = 0;
}

void build_voice(struct bytebuf *bb, struct bytebuf *tempobb, int vnum, int start, int end, int nextsync) {
	int s, t, i, tempo;
	uint8_t pendnote = 0xff, oob = 0;
	int pendwait = 0;
	uint8_t lastfx = 0xff, lastins = 0xff, lasttempo = 0xff;

	for(s = start; s < end; s++) {
		for(t = 0; t < song[s].length; t++) {
			if(vnum == 2) {
				tempo = 0;
				oob = 0;
				if(nextsync < nsyncpoint
				&& s == syncpoint[nextsync].songpos
				&& t == syncpoint[nextsync].trackpos) {
					if(syncpoint[nextsync].flags & SPF_LOOP) {
						oob |= 4;
					} else {
						oob |= 1;
						if(syncpoint[nextsync].flags & SPF_STREAM) {
							oob |= 4;
						}
					}
					nextsync++;
				}
				if(t == 0) {
					for(i = 0; i < 3; i++) {
						if(song[s].tt[i] > 0 && song[s].tt[i] < 0x40) {
							tempo = song[s].tt[i];
						}
					}
				}
				if(!tempo && s == 0 && t == 0) {
					tempo = 0x06;
				}
				if(tempo && (tempo & 0x0f) >= 4 && tempo != lasttempo) {
					oob |= 2;
					lasttempo = tempo;
				}
				if(oob) {
					flushpending(bb, &pendnote, &pendwait);
					putbyte(bb, 0xf8 | oob);
					if(oob & 2) {
						int even = tempo & 0x0f;
						int odd = even + ((tempo >> 4) & 3);
						putbyte(tempobb, (odd - 1) * 7);
						putbyte(tempobb, ((odd - 1) * 7) ^ ((even - 1) * 7));
					}
				}
			}
			if(track[song[s].ref[vnum]].line[t].fx < NFX) {
				if(track[song[s].ref[vnum]].line[t].fx != lastfx
				|| (track[song[s].ref[vnum]].line[t].note & 0x80)) {
					flushpending(bb, &pendnote, &pendwait);
					putbyte(bb, 0xc9 + fx[track[song[s].ref[vnum]].line[t].fx].nreloc);
					lastfx = track[song[s].ref[vnum]].line[t].fx;
				}
			}
			if(!(track[song[s].ref[vnum]].line[t].ins & 0x80)) {
				if(track[song[s].ref[vnum]].line[t].ins != lastins) {
					flushpending(bb, &pendnote, &pendwait);
					if(track[song[s].ref[vnum]].line[t].ins == 0x33) {
						putbyte(bb, 0x80);
					} else {
						putbyte(bb, 0x83 + ins[track[song[s].ref[vnum]].line[t].ins].nreloc);
					}
					if(track[song[s].ref[vnum]].line[t].ins < NINS) {
						lastins = track[song[s].ref[vnum]].line[t].ins;
					}
				}
			}
			if(!(track[song[s].ref[vnum]].line[t].note & 0x80)) {
				flushpending(bb, &pendnote, &pendwait);
				if(track[song[s].ref[vnum]].line[t].ins & 0x80) {
					putbyte(bb, 0x81);
				}
				pendnote = track[song[s].ref[vnum]].line[t].note;
				if(song[s].tt[vnum] >= 0x40 && song[s].tt[vnum] < 0xc0) {
					pendnote += song[s].tt[vnum] - 0x80;
				}
			} else {
				pendwait++;
			}
		}
	}
	if(end == songlen && !songloopflag) pendwait = 0;
	flushpending(bb, &pendnote, &pendwait);
}

void find_paths(struct decodestate *ds) {
	int pos, len, offset, bestoffset, bestlength;
	int transp, gottransp, besttransp, cycles;
	unsigned int cost, bestcost;
	uint8_t old, new;

	ds->paths = realloc(ds->paths, (ds->rledata.pos + 1) * sizeof(struct piece));
	ds->paths[ds->rledata.pos].cost = 0;
	ds->paths[ds->rledata.pos].length = 0;
	for(pos = ds->rledata.pos - 1; pos >= 0; pos--) {
		bestoffset = 0;
		bestlength = 1;
		besttransp = 0;
		bestcost = 2 + ds->paths[pos + 1].cost;
		for(len = 2; len <= 7 && pos + len <= ds->rledata.pos; len++) {
			cost = 1 + len + ds->paths[pos + len].cost;
			if(cost < bestcost) {
				bestcost = cost;
				bestlength = len;
			}
		}
		for(offset = 1; offset <= 256 && pos - offset >= 0; offset++) {
			gottransp = 0;
			transp = 0;
			cycles = 0;
			for(len = 0; len < 10 && pos + len < ds->rledata.pos; len++) {
				old = ds->rledata.buf[pos - offset + len];
				new = ds->rledata.buf[pos + len];
				if(old & 0x80) {
					if(old != new) break;
					cycles += 21;
					if(cycles > 229) break;
				} else if(new & 0x80) {
					break;
				} else if(gottransp) {
					old += transp * 2;
					if(old != new) break;
					cycles += 24;
					if(cycles > 229) break;
				} else if((new & 1) == (old & 1)) {
					transp = (new - old) / 2;
					if(transp < -15 || transp > 15) break;
					cycles += 24;
					if(cycles > 229) break;
					gottransp = 1;
				} else {
					break;
				}
			}
			if(len >= 3) {
				cost = 2 + ds->paths[pos + len].cost;
				if(cost < bestcost) {
					bestcost = cost;
					bestlength = len;
					bestoffset = offset;
					besttransp = transp;
				}
			}
		}
		ds->paths[pos].offset = bestoffset;
		ds->paths[pos].length = bestlength;
		ds->paths[pos].transp = besttransp;
		ds->paths[pos].cost = bestcost;
	}

	//fprintf(stderr, "%d\n", ds->paths[0].cost);
}

void crunch_some(struct decodestate *ds, struct bytebuf *bb) {
	int len, i;
	struct piece *p;

	if(ds->wpos - ds->rpos < 128) {
		if(ds->wpos - ds->rpos < 4) {
			len = ds->rledata.pos - ds->wpos;
			if(len > 7) len = 7;
			if(len > 0) {
				if(verbose >= 2) fprintf(stderr, "%d: Forced literal %d [", ds->vnum, len);
				putbyte(bb, len);
				ds->bytes++;
				for(i = 0; i < len; i++) {
					if(verbose >= 2) {
						fprintf(stderr, "%02x", ds->rledata.buf[ds->wpos]);
						fprintf(stderr, (i == len - 1)? "]\n" : " ");
					}
					putbyte(bb, ds->rledata.buf[ds->wpos++]);
					ds->bytes++;
				}
			} else {
				if(verbose >= 2) fprintf(stderr, "%d: Pad\n", ds->vnum);
				putbyte(bb, 0x87);
				putbyte(bb, (ds->wpos - 1) & 0xff);
				ds->bytes += 2;
				ds->wpos += 10;
			}
		} else {
			p = (ds->wpos < ds->rledata.pos)? &ds->paths[ds->wpos] : 0;
			if(!p) {
				if(verbose >= 2) fprintf(stderr, "%d: Pad\n", ds->vnum);
				putbyte(bb, 0x87);
				putbyte(bb, (ds->wpos - 1) & 0xff);
				ds->bytes += 2;
				ds->wpos += 10;
			} else if(!p->offset) {
				if(verbose >= 2) fprintf(stderr, "%d: Literal %d [", ds->vnum, p->length);
				putbyte(bb, p->length);
				ds->bytes++;
				for(i = 0; i < p->length; i++) {
					if(verbose >= 2) {
						fprintf(stderr, "%02x", ds->rledata.buf[ds->wpos]);
						fprintf(stderr, (i == p->length - 1)? "]\n" : " ");
					}
					putbyte(bb, ds->rledata.buf[ds->wpos++]);
					ds->bytes++;
				}
			} else {
				if(verbose >= 2) {
					fprintf(stderr, "%d: Copy %d (transp %d, offset %d) [",
						ds->vnum,
						p->length,
						p->transp,
						p->offset);
					for(i = 0; i < p->length; i++) {
						fprintf(stderr, "%02x", ds->rledata.buf[ds->wpos + i]);
						fprintf(stderr, (i == p->length - 1)? "]\n" : " ");
					}
				}
				putbyte(bb, ((p->transp + 16) << 3) + p->length - 3);
				if(songloopflag) {
					putbyte(bb, (-p->offset - p->length) & 0xff);
				} else {
					putbyte(bb, (ds->wpos - p->offset) & 0xff);
				}
				ds->bytes += 2;
				ds->wpos += p->length;
			}
		}
	} else {
		if(verbose >= 2) fprintf(stderr, "%d: Holding flow.\n", ds->vnum);
	}
}

uint8_t getbyte(struct decodestate *ds) {
	if(ds->rpos >= ds->rledata.pos) {
		ds->rpos++;
		return 0xc0;
	} else {
		return ds->rledata.buf[ds->rpos++];
	}
}

void ungetbyte(struct decodestate *ds) {
	ds->rpos--;
}

void run_prep1(struct decodestate *ds, uint8_t *pend_oob) {
	uint8_t b;

	ds->timer++;
	if(!(ds->timer & 0x80)) {
		b = getbyte(ds);
		if(b >= 0xf9) {
			*pend_oob = b;
			b = getbyte(ds);
		}
		if(b >= 0xc9) {
		} else {
			ungetbyte(ds);
		}
	}
}

void run_prep2(struct decodestate *ds) {
	uint8_t b;

	if(!(ds->timer & 0x80)) {
		b = getbyte(ds);
		if(b >= 0x80 && b <= 0xb2) {
		} else {
			ungetbyte(ds);
		}
	}
}

void run_prep3(struct decodestate *ds) {
	uint8_t b;

	if(!(ds->timer & 0x80)) {
		b = getbyte(ds);
		if(b >= 0xb8 && b <= 0xc7) {
			ds->timer = 0xf0 | b;
		} else if(b < 0x80) {
			ds->timer = 0xfe | b;
		} else errx(1, "Internal stream error, %02x, voice %d", b, ds->vnum);
	}
}

void crunch_streams(struct decodestate *vdecode, struct bytebuf *streambb, struct bytebuf *tempodata, int *currstream, int *tempopos) {
	int i;
	uint8_t pend_oob;

	for(i = 0; i < 3; i++) {
		vdecode[i].timer = 0xff;
	}

	while(
		vdecode[0].rpos < vdecode[0].rledata.pos ||
		vdecode[1].rpos < vdecode[1].rledata.pos ||
		vdecode[2].rpos < vdecode[2].rledata.pos
	) {
		pend_oob = 0;
		crunch_some(&vdecode[2], &streambb[*currstream]);
		for(i = 2; i >= 0; i--) {
			run_prep1(&vdecode[i], &pend_oob);
		}
		crunch_some(&vdecode[1], &streambb[*currstream]);
		for(i = 2; i >= 0; i--) {
			run_prep2(&vdecode[i]);
		}
		crunch_some(&vdecode[0], &streambb[*currstream]);
		for(i = 2; i >= 0; i--) {
			run_prep3(&vdecode[i]);
		}
		if(pend_oob & 0x02) {
			if(verbose >= 2) fprintf(stderr, "OOB: Tempo bytes ($%02x $%02x)\n",
				tempodata->buf[*tempopos + 1],
				tempodata->buf[*tempopos + 0]);
			putbyte(&streambb[*currstream], tempodata->buf[(*tempopos)++]);
			putbyte(&streambb[*currstream], tempodata->buf[(*tempopos)++]);
		}
		if(pend_oob & 0x04) {
			(*currstream)++;
		}
	}
}

int allocdata(uint8_t *src, int len, struct bytebuf *bb, char *tag, char id) {
	int i, result = -1, found = 0;

	i = strcmp(tag, "FIL") ? 0 : 4;	// filter table offset 0 means "don't grab"
	while(i <= bb->pos - len) {
		if(!memcmp(bb->buf + i, src, len)) {
			result = i;
			found = 1;
			break;
		} else {
			i++;
		}
	}

	if(!found) {
		result = bb->pos;
		for(i = 0; i < len; i++) {
			putbyte(bb, src[i]);
		}
		if(bb->pos > 256) errx(1, "Overflow in %s data", tag);
	}

	if(verbose >= 2) {
		fprintf(stderr, "%s %c:", tag, id);
		for(i = 0; i < len; i++) fprintf(stderr, " %02x", src[i]);
		fprintf(stderr, found? " (found matching bytes)\n" : "\n");
	}

	return result;
}

void addsync(char *spec, int line, char *fname) {
	int sp, tp, addr;
	char *ptr;

	if(nsyncpoint >= MAXSYNC) errx(1, "Too many syncpoints");

	sp = strtol(spec, &ptr, 16);
	if(sp < 0 || sp > 0xff) goto error;
	if(!ptr || *ptr != ':') goto error;
	ptr++;

	tp = strtol(ptr, &ptr, 16);
	if(tp < 0 || tp >= 0x20) goto error;

	if(ptr && *ptr) {
		if(*ptr != ':') goto error;
		ptr++;

		addr = strtol(ptr, &ptr, 16);
		if(addr < 2 || addr > 0xffff) goto error;
		if(!ptr || *ptr != ':') goto error;
		ptr++;

		stream[nstream].filename = strdup(ptr);
		stream[nstream].addr = addr;
		nstream++;
		syncpoint[nsyncpoint].flags = SPF_STREAM;
	} else {
		syncpoint[nsyncpoint].flags = 0;
	}
	syncpoint[nsyncpoint].songpos = sp;
	syncpoint[nsyncpoint].trackpos = tp;
	nsyncpoint++;

	return;
error:
	if(fname) {
		errx(1, "%s:%d: Invalid syncpoint specification", fname, line);
	} else {
		errx(1, "Invalid syncpoint specification");
	}
}

void loadsyncfile(char *fname) {
	FILE *f;
	char buf[512];
	int p, line = 1;

	f = fopen(fname, "r");
	if(!f) err(1, "%s", fname);

	while(fgets(buf, sizeof(buf), f)) {
		if(*buf && buf[strlen(buf) - 1] == '\n') buf[strlen(buf) - 1] = 0;
		if(*buf && buf[strlen(buf) - 1] == '\r') buf[strlen(buf) - 1] = 0;
		if(*buf && (*buf != '#')) {
			for(p = 0; buf[p]; p++) {
				if(buf[p] == '@') break;
			}
			if(buf[p]) {
				addsync(buf + p + 1, line, fname);
			}
		}
		line++;
	}

	fclose(f);
}

static void usage(char *prgname) {
	fprintf(stderr, "Birdcruncher " VERSION "\n\n");
	fprintf(stderr, "Usage: %s [options] songfile\n", prgname);
	fprintf(stderr, "Options (numerical arguments must be in hexadecimal, no prefix):\n");
	fprintf(stderr, "  -h --help        Display this text.\n");
	fprintf(stderr, "  -V --version     Display version information.\n");
	fprintf(stderr, "\n");
	fprintf(stderr, "  -v --verbose     Be verbose. Can be specified multiple times.\n");
	fprintf(stderr, "\n");
	fprintf(stderr, "  -o --output      Output filename. Default: a.sid / a.prg\n");
	fprintf(stderr, "  -t --format      Output format (sid, prg, dist). Default: sid\n");
	fprintf(stderr, "\n");
	fprintf(stderr, "Format-specific options for 'sid':\n");
	fprintf(stderr, "  -a --address     Set start address of player. Default: 1000\n");
	fprintf(stderr, "  -z --zeropage    Set start of zero-page area (16 bytes). Default: e0\n");
	fprintf(stderr, "  -u --unpack      Set start of unpack buffer (3 pages). Default: In player.\n");
	fprintf(stderr, "  -s --sync        Add syncpoint: ss:tt\n");
	fprintf(stderr, "  -@ --syncfile    Read syncpoint directives from a file.\n");
	fprintf(stderr, "  -O --oldsid      Mark file as intended for old sid chip.\n");
	fprintf(stderr, "  -N --newsid      Mark file as intended for new sid chip (default).\n");
	fprintf(stderr, "\n");
	fprintf(stderr, "Format-specific options for 'prg':\n");
	fprintf(stderr, "  -f --fg          Foreground colour\n");
	fprintf(stderr, "  -b --bg          Background and border colour\n");
	fprintf(stderr, "  -r --raster      Rastertime indicator colour\n");
	fprintf(stderr, "\n");
	fprintf(stderr, "Format-specific options for 'dist':\n");
	fprintf(stderr, "  -a --address     Set start address of player. Default: 1000\n");
	fprintf(stderr, "  -z --zeropage    Set start of zero-page area (16 bytes). Default: e0\n");
	fprintf(stderr, "  -u --unpack      Set start of unpack buffer (3 pages). Default: After player.\n");
	fprintf(stderr, "  -i --init        Store init-routine separately: addr:filename\n");
	fprintf(stderr, "  -s --sync        Add syncpoint/chunk: ss:tt[:addr:filename]\n");
	fprintf(stderr, "  -@ --syncfile    Read syncpoint/chunk directives from a file.\n");
	exit(1);
}

int main(int argc, char **argv) {
	struct option longopts[] = {
		{"help", 0, 0, 'h'},
		{"version", 0, 0, 'V'},
		{"verbose", 0, 0, 'v'},
		{"output", 1, 0, 'o'},
		{"format", 1, 0, 't'},
		{"address", 1, 0, 'a'},
		{"zeropage", 1, 0, 'z'},
		{"sync", 1, 0, 's'},
		{"newsid", 0, 0, 'N'},
		{"oldsid", 0, 0, 'O'},
		{"fg", 1, 0, 'f'},
		{"bg", 1, 0, 'b'},
		{"raster", 1, 0, 'r'},
		{"unpack", 1, 0, 'u'},
		{"init", 1, 0, 'i'},
		{"syncfile", 1, 0, '@'},
		{0, 0, 0, 0}
	};
	int h, i, j, opt, pos, sz, target, nins = 0, ins_restart[2], nfx = 0, tempopos;
	uint8_t waveform;
	uint8_t insref[NINS], fxref[NFX], data[256];
	struct bytebuf tempodata, streambb[MAXSYNC + 1];
	struct decodestate vdecode[3];
	int currstream;
	char *prgname = argv[0];
	char *outname = 0;
	char *initfile = 0;
	int format = FMT_SID;
	int oldsid = 0, newsid = 0;
	struct ext_symbols syms;
	uint16_t org;
	uint8_t zpbase = 0;
	uint16_t resident = 0, initorg = 0, unpackorg = 0;
	int padding, residentsize;
	FILE *f;
	int repeatptr = 0;
	int fgcol = -1, bgcol = -1, rastcol = -1;
	char *ptr;
	struct bytebuf savedrle[2];

	do {
		opt = getopt_long(argc, argv, "?hVvo:t:a:z:s:NOf:b:r:u:i:@:", longopts, 0);
		switch(opt) {
			case 0:
			case '?':
			case 'h':
				usage(prgname);
				break;
			case 'V':
				fprintf(stderr, "%s\n", VERSION);
				exit(0);
			case 'v':
				verbose++;
				break;
			case 'o':
				outname = strdup(optarg);
				break;
			case 't':
				if(!strcmp(optarg, "sid")) {
					format = FMT_SID;
				} else if(!strcmp(optarg, "prg")) {
					format = FMT_PRG;
				} else if(!strcmp(optarg, "dist")) {
					format = FMT_DIST;
				} else {
					errx(1, "Unknown format '%s'", optarg);
				}
				break;
			case 'a':
				resident = strtol(optarg, 0, 16);
				if(resident < 0x100 || resident > 0xffff) errx(1, "Parameter out of range");
				break;
			case 'z':
				zpbase = strtol(optarg, 0, 16);
				if(zpbase < 2 || zpbase > 0xf0) errx(1, "Parameter out of range");
				break;
			case 's':
				addsync(optarg, 0, 0);
				break;
			case 'N':
				newsid = 1;
				break;
			case 'O':
				oldsid = 1;
				break;
			case 'f':
				fgcol = strtol(optarg, 0, 16);
				if(fgcol < 0 || fgcol > 0xf) errx(1, "Invalid colour");
				break;
			case 'b':
				bgcol = strtol(optarg, 0, 16);
				if(bgcol < 0 || bgcol > 0xf) errx(1, "Invalid colour");
				break;
			case 'r':
				rastcol = strtol(optarg, 0, 16);
				if(rastcol < 0 || rastcol > 0xf) errx(1, "Invalid colour");
				break;
			case 'u':
				unpackorg = strtol(optarg, 0, 16);
				if(unpackorg < 2 || unpackorg > 0xffff) errx(1, "Invalid unpack address");
				break;
			case 'i':
				initorg = strtol(optarg, &ptr, 16);
				if(initorg < 2 || initorg > 0xffff) errx(1, "Invalid init address");
				if(!ptr || *ptr != ':') errx(1, "Syntax error in -i parameter");
				initfile = strdup(ptr + 1);
				break;
			case '@':
				loadsyncfile(optarg);
				break;
			default:
				if(opt >= 0) errx(1, "Unimplemented option '%c'", opt);
				break;
		}
	} while(opt >= 0);

	if(optind != argc - 1) usage(prgname);

	loadfile(argv[optind]);

	switch(format) {
	case FMT_SID:
		if(fgcol >= 0 || bgcol >= 0 || rastcol >= 0) {
			errx(1, "Colours cannot be specified for 'sid' format");
		}
		if(initorg) {
			errx(1, "Init routine cannot be relocated for 'sid' format");
		}
		break;
	case FMT_PRG:
		if(resident || zpbase || initorg || unpackorg) {
			errx(1, "Target addresses cannot be specified for 'prg' format");
		}
		if(nsyncpoint) {
			errx(1, "Syncpoints cannot be specified for 'prg' format");
		}
		if(oldsid || newsid) {
			errx(1, "SID model cannot be specified for 'prg' format");
		}
		break;
	case FMT_DIST:
		if(songloopflag) {
			errx(1, "Repeating songs cannot be combined with the 'dist' format.");
		}
		if(oldsid || newsid) {
			errx(1, "SID model cannot be specified for 'dist' format");
		}
		if(!nstream) {
			errx(1, "No chunks specified!");
		}
		if(syncpoint[0].songpos
		|| syncpoint[0].trackpos
		|| !(syncpoint[0].flags & SPF_STREAM)) {
			errx(1, "First chunk must be at position 00:00");
		}
		if(fgcol >= 0 || bgcol >= 0 || rastcol >= 0) {
			errx(1, "Colours cannot be specified for 'dist' format");
		}
		break;
	}

	if(!outname) {
		outname = (format == FMT_SID)? "a.sid" : "a.prg";
	}
	if(!oldsid && !newsid) newsid = 1;

	if(!resident) resident = 0x1000;
	if(!zpbase) zpbase = 0xe0;

	if(resident & 0xff) errx(1, "Player must be page-aligned");
	if(unpackorg & 0xff) errx(1, "Unpack buffer must be page-aligned");

	for(i = 0; i < nsyncpoint; i++) {
		if(syncpoint[i].songpos >= songlen
		|| syncpoint[i].trackpos >= song[syncpoint[i].songpos].length) {
			errx(1, "Syncpoint #%d outside song or track.", i + 1);
		}
		if(i &&
			(syncpoint[i - 1].songpos > syncpoint[i].songpos
			|| (syncpoint[i - 1].songpos == syncpoint[i].songpos
				&& syncpoint[i - 1].trackpos >= syncpoint[i].trackpos)))
		{
			errx(1, "Duplicate or disordered syncpoints.");
		}
	}

	if(verbose >= 1 && nsyncpoint) {
		fprintf(stderr, "%d syncpoints:\n", nsyncpoint);
		j = 0;
		for(i = 0; i < nsyncpoint; i++) {
			if(syncpoint[i].flags & SPF_STREAM) {
				fprintf(stderr, "Chunk at %04x: (%s)\n", stream[j].addr, stream[j].filename);
				j++;
			}
			fprintf(stderr, "\tSyncpoint %02x:%02x\n", syncpoint[i].songpos, syncpoint[i].trackpos);
		}
	}

	for(i = 0; i < songlen; i++) {
		for(j = 0; j < 3; j++) {
			track[song[i].ref[j]].used = 1;
		}
	}

	for(i = 0; i < 256; i++) {
		if(track[i].used) {
			for(j = 0; j < track[i].length; j++) {
				if(track[i].line[j].ins < NINS) {
					ins[track[i].line[j].ins].used = 1;
				}
				if(track[i].line[j].fx < NFX) {
					fx[track[i].line[j].fx].used = 1;
				}
			}
		}
	}

	for(i = 0; i < NINS; i++) {
		if(ins[i].h == 2 && ins[i].ad >= 0x20) ins[i].h = 1;
	}

	for(h = 0; h <= 2; h++) {
		if(h) ins_restart[h - 1] = nins;
		for(i = 0; i < NINS; i++) {
			if(ins[i].used && ins[i].h == h) {
				insref[nins] = i;
				ins[i].nreloc = nins++;
			}
		}
	}

	for(i = 0; i < NFX; i++) {
		if(fx[i].used) {
			fxref[nfx] = i;
			fx[i].nreloc = nfx++;
		}
	}

	putbyte(&filtertbl, 0x1f);
	putbyte(&filtertbl, 0x00);
	putbyte(&filtertbl, 0x80);
	putbyte(&filtertbl, 0xff);

	sz = 0;
	for(i = 0; i < NINS; i++) {
		if(ins[i].used && ins[i].flength > sz) sz = ins[i].flength;
	}
	for(; sz > 0; sz--) {
		for(i = 0; i < NINS; i++) {
			if(ins[i].used && ins[i].flength == sz) {
				pos = 0;
				for(j = 0; j < ins[i].flength; j++) {
					data[pos++] = ins[i].filter1[j] | 0x0f;
					data[pos++] = ins[i].filter2[j];
					switch(ins[i].filter1[j] & 0x0f) {
					case 0:
						data[pos++] = ((ins[i].filter3[j] ^ 0x80) >> 1) | 0x80;
						break;
					case 1:
						data[pos++] = (ins[i].filter3[j] & 0x3f) | 0x00;
						break;
					case 2:
						data[pos++] = ((-ins[i].filter3[j]) & 0x3f) | 0x40;
						break;
					}
				}
				data[pos++] = (((ins[i].floop - ins[i].flength) * 3) + 2) & 0xff;
				ins[i].fstart = allocdata(data, pos, &filtertbl, "FIL", namechar[i]);
			}
		}
	}

	sz = 0;
	for(i = 0; i < NINS; i++) {
		if(ins[i].used && ins[i].wlength > sz) sz = ins[i].wlength;
	}
	for(; sz > 0; sz--) {
		for(i = 0; i < NINS; i++) {
			if(ins[i].used && ins[i].wlength == sz) {
				pos = 0;
				target = 0;
				for(j = 0; j < ins[i].wlength; j++) {
					if(ins[i].wloop == j) target = pos;
					waveform = ins[i].wave1[j];
					if(waveform >= 0xc0) waveform = (waveform & 0x7f) | 0x08;
					data[pos++] = waveform;
					if(waveform & 0x40) {
						if(!ins[i].wave2[j]) {
							data[pos++] = (ins[i].wave3[j] >> 1) | 0x80;
						} else {
							if(ins[i].wave3[j] > 0x7f) {
								data[pos++] = 0x7f;
							} else {
								data[pos++] = ins[i].wave3[j] & 0x7f;
							}
						}
					}
				}
				data[pos] = (target - pos - 1) & 0xff;
				ins[i].wstart = allocdata(data, ++pos, &wavetbl, "WAV", namechar[i]);
			}
		}
	}

	sz = 0;
	for(i = 0; i < NFX; i++) {
		if(fx[i].used && fx[i].length > sz) sz = fx[i].length;
	}
	for(; sz > 0; sz--) {
		for(i = 0; i < NFX; i++) {
			if(fx[i].used && fx[i].length == sz) {
				for(j = 0; j < sz; j++) data[j] = fx[i].data[j];
				data[sz] = (fx[i].loop - fx[i].length) & 0xff;
				fx[i].start = allocdata(data, sz + 1, &fxtbl, "FX ", namechar[i]);
			}
		}
	}

	if(verbose >= 1) {
		fprintf(stderr, "Filter %d, wave %d, fx %d, total %d\n",
			filtertbl.pos,
			wavetbl.pos,
			fxtbl.pos,
			filtertbl.pos + wavetbl.pos + fxtbl.pos);
	}

	if(verbose >= 1) {
		fprintf(stderr, "Crunching track and song data...\n");
	}

	memset(streambb, 0, sizeof(streambb));

	if(songloopflag && songloop) {
		for(i = 0; i < nsyncpoint; i++) {
			if(syncpoint[i].songpos >= songloop) break;
		}
		memmove(syncpoint + i + 1, syncpoint + i, sizeof(struct syncpoint) * (nsyncpoint - i));
		syncpoint[i].songpos = songloop - 1;
		syncpoint[i].trackpos = song[songloop - 1].length - 1;
		syncpoint[i].flags = SPF_LOOP;
		repeatptr = i + 1;
		nsyncpoint++;
		syncpoint[nsyncpoint].songpos = songlen - 1;
		syncpoint[nsyncpoint].trackpos = song[songlen - 1].length - 1;
		syncpoint[nsyncpoint].flags = SPF_LOOP;
		nsyncpoint++;

		memset(&tempodata, 0, sizeof(struct bytebuf));
		tempopos = 0;
		for(i = 0; i < 3; i++) {
			memset(&vdecode[i], 0, sizeof(struct decodestate));
			vdecode[i].vnum = i;
			build_voice(&vdecode[i].rledata, &tempodata, i, songloop, songlen, repeatptr);
			if(i < 2) {
				if(!vdecode[i].rledata.pos) {
					putbyte(&vdecode[i].rledata, 0xc0);
				}
				for(j = 0; j < 7; j++) {
					putbyte(&vdecode[i].rledata, vdecode[i].rledata.buf[j % vdecode[i].rledata.pos]);
				}
			}
		}

		memset(&savedrle, 0, sizeof(savedrle));
		for(i = 0; i < 2; i++) {
			for(j = 0; j < 7; j++) {
				putbyte(&savedrle[i], vdecode[i].rledata.buf[j % vdecode[i].rledata.pos]);
			}
		}

		for(i = 0; i < 3; i++) {
			find_paths(&vdecode[i]);
			vdecode[i].rpos = 0;
			vdecode[i].wpos = i < 2? 7 : 0;
		}
		currstream = 2;
		crunch_streams(vdecode, streambb, &tempodata, &currstream, &tempopos);
		if(currstream != 3) errx(1, "Internal error (1)");

		memset(&tempodata, 0, sizeof(struct bytebuf));
		tempopos = 0;
		for(i = 0; i < 3; i++) {
			vdecode[i].rledata.pos = 0;
			build_voice(&vdecode[i].rledata, &tempodata, i, 0, songloop, 0);
			if(i < 2) {
				for(j = 0; j < savedrle[i].pos; j++) {
					putbyte(&vdecode[i].rledata, savedrle[i].buf[j]);
				}
			}
		}
		for(i = 0; i < 3; i++) {
			find_paths(&vdecode[i]);
			vdecode[i].rpos = 0;
			vdecode[i].wpos = 0;
		}
		currstream = 0;
		crunch_some(&vdecode[1], &streambb[currstream]);
		crunch_some(&vdecode[0], &streambb[currstream]);
		crunch_streams(vdecode, streambb, &tempodata, &currstream, &tempopos);
		if(currstream != 1) errx(1, "Internal error (2)");
	} else {
		if(songloopflag) {
			syncpoint[nsyncpoint].songpos = songlen - 1;
			syncpoint[nsyncpoint].trackpos = song[songlen - 1].length - 1;
			syncpoint[nsyncpoint].flags = SPF_LOOP;
			nsyncpoint++;
		}

		memset(&tempodata, 0, sizeof(struct bytebuf));
		tempopos = 0;
		for(i = 0; i < 3; i++) {
			memset(&vdecode[i], 0, sizeof(struct decodestate));
			vdecode[i].vnum = i;
			build_voice(&vdecode[i].rledata, &tempodata, i, 0, songlen, (format == FMT_DIST));
			if(songloopflag) {
				if(i < 2) {
					if(!vdecode[i].rledata.pos) {
						putbyte(&vdecode[i].rledata, 0xc0);
					}
					for(j = 0; j < 7; j++) {
						putbyte(&vdecode[i].rledata, vdecode[i].rledata.buf[j % vdecode[i].rledata.pos]);
					}
				}
			} else {
				putbyte(&vdecode[i].rledata, 0xc0);	// will be copied many times for padding
			}
		}
		for(i = 0; i < 3; i++) {
			find_paths(&vdecode[i]);
			vdecode[i].rpos = 0;
			vdecode[i].wpos = 0;
		}

		currstream = 0;
		crunch_some(&vdecode[1], &streambb[currstream]);
		crunch_some(&vdecode[0], &streambb[currstream]);
		repeatptr = streambb[currstream].pos;

		crunch_streams(vdecode, streambb, &tempodata, &currstream, &tempopos);

		if(!songloopflag) {
			if(verbose >= 2) fprintf(stderr, "OOB: Stop\n");
			putbyte(&streambb[currstream], 0);
		}
	}

	if(verbose >= 1) {
		for(i = 0; i < 3; i++) {
			if(vdecode[i].rledata.pos) {
				fprintf(stderr, "Voice %d packed %d -> %d (%d%%)\n",
					i + 1,
					vdecode[i].rledata.pos,
					vdecode[i].bytes,
					vdecode[i].bytes * 100 / vdecode[i].rledata.pos);
			}
		}
	}

	f = fopen(outname, "wb");
	if(!f) err(1, "%s", outname);

	syms.INS_RESTART = ins_restart[0];
	syms.INS_RESTART2 = ins_restart[1];
	syms.zp_base = zpbase;

	if(format == FMT_PRG) {
		org = 0x801 - 2;	org += sizeof(seg_prghead_data);
		syms.metadata = org;	org += 3 * 32;
		resident = org = 0x900;
		syms.sidorg = org;
		syms.fgcol = (fgcol >= 0)? fgcol : 0xf;
		syms.bgcol = (bgcol >= 0)? bgcol : 0x0;
		syms.rastcol = (rastcol >= 0)? rastcol : 0x9;
		seg_prghead_reloc(&syms);
	}

	org = resident;
	if(songloopflag) {
		syms.seg_rplay = org;	org += sizeof(seg_rplay_data);
	} else {
		syms.seg_play = org;	org += sizeof(seg_play_data);
	}
	syms.ins_ad = org;	org += nins;
	syms.ins_sr = org;	org += nins;
	syms.ins_wave = org;	org += nins;
	syms.ins_filt = org;	org += nins;
	syms.fx_start = org;	org += nfx;
	syms.filttable = org;	org += filtertbl.pos;
	syms.fxtable = org;	org += fxtbl.pos;
	syms.wavetable = org;	org += wavetbl.pos;

	if(initorg) {
		syms.seg_init = initorg;
	} else {
		if(songloopflag) {
			syms.seg_rinit = org;	org += sizeof(seg_rinit_data);
		} else{
			syms.seg_init = org;	org += sizeof(seg_init_data);
		}
	}
	residentsize = org - resident;

	if(format == FMT_DIST) {
		for(i = nstream - 2; i >= 0; i--) {
			uint16_t addr = stream[i + 1].addr + streambb[i + 1].pos - 1;
			putbyte(&streambb[i], addr >> 8);
			putbyte(&streambb[i], addr & 0xff);
		}
		syms.streamstart = stream[0].addr + streambb[0].pos - 1;
	} else if(songloopflag && songloop) {
		org += 2;
		org += streambb[2].pos;
		repeatptr = org - 1;
		org += 2;
		org += streambb[0].pos;
		syms.streamstart = org - 1;
	} else {
		if(songloopflag) org += 2;
		org += streambb[0].pos;
		syms.streamstart = org - 1;
	}

	if(unpackorg) {
		syms.unpackbufs = unpackorg;
		padding = 0;
	} else {
		padding = ((org + 0xff) & 0xff00) - org;
		org += padding;
		syms.unpackbufs = org;	org += 0x300;
		padding += 0x300;
	}

	if(songloopflag) {
		seg_rplay_reloc(&syms);
		seg_rinit_reloc(&syms);
	} else {
		seg_play_reloc(&syms);
		seg_init_reloc(&syms);
	}

	if(format == FMT_SID) {
		fwrite("PSID", 4, 1, f);
		fputc(0, f);
		fputc(2, f);
		fputc(0, f);
		fputc(0x7c, f);
		fputc(0, f);
		fputc(0, f);
		fputc((resident + 0) >> 8, f);
		fputc((resident + 0) & 0xff, f);
		fputc((resident + 3) >> 8, f);
		fputc((resident + 3) & 0xff, f);
		fputc(0, f);
		fputc(1, f);
		fputc(0, f);
		fputc(1, f);
		fputc(0, f);
		fputc(0, f);
		fputc(0, f);
		fputc(0, f);
		fwrite(&header[0x61f0 - FILEORG], 3 * 32, 1, f);
		fputc(0, f);
		fputc(0x04 | (oldsid? 0x10 : 0) | (newsid? 0x20 : 0), f);
		if(unpackorg) {
			uint8_t page[256];
			int best = 0, bestlen = 0;

			memset(page, 0, sizeof(page));
			for(i = 0x00; i <= 0x03; i++) page[i] = 1;
			for(i = 0xa0; i <= 0xbf; i++) page[i] = 1;
			for(i = 0xd0; i <= 0xff; i++) page[i] = 1;
			for(i = resident >> 8; i <= (org - 1) >> 8; i++) page[i] = 1;
			for(i = unpackorg >> 8; i <= (unpackorg + 0x2ff) >> 8; i++) page[i] = 1;
			for(i = 0; i <= 0xff; i++) {
				for(j = 0; i + j <= 0xff; j++) if(page[i + j]) break;
				if(j > bestlen) {
					bestlen = j;
					best = i;
				}
				i += j;
			}
			fputc(best, f);
			fputc(bestlen, f);
		} else {
			fputc(0, f);
			fputc(0, f);
		}
		fputc(0, f);
		fputc(0, f);
		fputc(resident & 0xff, f);
		fputc(resident >> 8, f);
	} else if(format == FMT_DIST) {
		fputc(resident & 0xff, f);
		fputc(resident >> 8, f);
	} else {
		fwrite(seg_prghead_data, sizeof(seg_prghead_data), 1, f);
		for(i = 0; i < 3 * 32; i++) {
			fputc(pet2scr[flipcase(header[0x61f0 - FILEORG + i])], f);
		}
		for(i = 0x801 - 2 + sizeof(seg_prghead_data) + 3 * 32; i < resident; i++) {
			fputc(0, f);
		}
	}

	if(songloopflag) {
		fwrite(seg_rplay_data, sizeof(seg_rplay_data), 1, f);
	} else {
		fwrite(seg_play_data, sizeof(seg_play_data), 1, f);
	}
	for(i = 0; i < nins; i++) fputc(ins[insref[i]].ad, f);
	for(i = 0; i < nins; i++) fputc(ins[insref[i]].sr, f);
	for(i = 0; i < nins; i++) fputc(ins[insref[i]].wstart, f);
	for(i = 0; i < nins; i++) fputc(ins[insref[i]].fstart, f);
	for(i = 0; i < nfx; i++) fputc(fx[fxref[i]].start, f);
	fwrite(filtertbl.buf, filtertbl.pos, 1, f);
	fwrite(fxtbl.buf, fxtbl.pos, 1, f);
	fwrite(wavetbl.buf, wavetbl.pos, 1, f);
	if(!initorg) {
		if(songloopflag) {
			fwrite(seg_rinit_data, sizeof(seg_rinit_data), 1, f);
		} else {
			fwrite(seg_init_data, sizeof(seg_init_data), 1, f);
		}
	}
	if(format != FMT_DIST) {
		if(songloopflag && songloop) {
			fputc(repeatptr & 0xff, f);
			fputc(repeatptr >> 8, f);
			for(i = streambb[2].pos - 1; i >= 0; i--) {
				fputc(streambb[2].buf[i], f);
			}
			fputc(repeatptr & 0xff, f);
			fputc(repeatptr >> 8, f);
			for(i = streambb[0].pos - 1; i >= 0; i--) {
				fputc(streambb[0].buf[i], f);
			}
		} else {
			if(songloopflag) {
				fputc((syms.streamstart - repeatptr) & 0xff, f);
				fputc((syms.streamstart - repeatptr) >> 8, f);
			}
			for(i = streambb[0].pos - 1; i >= 0; i--) {
				fputc(streambb[0].buf[i], f);
			}
		}

		if(format == FMT_SID) {
			for(i = 0; i < padding; i++) fputc(0, f);
		}
	}

	fclose(f);

	if(format == FMT_DIST) {
		if(verbose >= 1) {
			fprintf(stderr, "%04x-%04x Resident player%s\n",
				resident,
				resident + residentsize - 1,
				initorg? "" : " + init routine");
		}
		if(initorg) {
			if(verbose >= 1) {
				fprintf(stderr, "%04x-%04x Init routine\n",
					initorg,
					(int) (initorg + sizeof(seg_init_data) - 1));
			}
			f = fopen(initfile, "wb");
			if(!f) err(1, "%s", initfile);

			fputc(initorg & 0xff, f);
			fputc(initorg >> 8, f);
			fwrite(seg_init_data, sizeof(seg_init_data), 1, f);

			fclose(f);
		}
		if(verbose >= 1) {
			fprintf(stderr, "%04x-%04x Unpack buffers\n",
				syms.unpackbufs,
				syms.unpackbufs + 0x2ff);
		}

		for(i = 0; i < nstream; i++) {
			if(verbose >= 1) {
				fprintf(stderr, "%04x-%04x Stream chunk #%d\n",
					stream[i].addr,
					stream[i].addr + streambb[i].pos - 1,
					i + 1);
			}
			f = fopen(stream[i].filename, "wb");
			if(!f) err(1, "%s", stream[i].filename);

			fputc(stream[i].addr & 0xff, f);
			fputc(stream[i].addr >> 8, f);
			for(j = streambb[i].pos - 1; j >= 0; j--) {
				fputc(streambb[i].buf[j], f);
			}

			fclose(f);
		}
	}

	return 0;
}
