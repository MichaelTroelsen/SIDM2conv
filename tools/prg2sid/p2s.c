/* PRG 2 SID (/) iAN CooG/HVSC
   Automatically attach a PSID header to a ripped (prg) tune.
   Identifies some players and sets init/play accordingly, also patches
   the header/code if needed.
*/
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#ifdef _WIN32
#include <windows.h>
//#pragma warning(disable:4996)
#else
#define MAX_PATH 260
#endif
#define VERSION "1.25"
#define P_MARKER   0x00
#define P_SIDVER   0x05
#define P_INITADDR 0x0a
#define P_PLAYADDR 0x0c
#define P_SUBTUNES 0x0f
#define P_STARTSNG 0x11
#define P_TIMING   0x15
#define P_NAME     0x16
#define P_AUTHOR   0x36
#define P_RELEASED 0x56
#define P_SIDMODEL 0x77
#define P_FREEPAGE 0x78
#define P_FREEPMAX 0x79
#define P_STEREOAD 0x7a
unsigned char psidh[0x7c]={
0x50,0x53,0x49,0x44,0x00,0x02,0x00,0x7C,0x00,0x00,0x10,0x00,0x10,0x03,0x00,0x01,
0x00,0x01,0x00,0x00,0x00,0x00,0x3C,0x3F,0x3E,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
0x00,0x00,0x00,0x00,0x00,0x00,0x3C,0x3F,0x3E,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
0x00,0x00,0x00,0x00,0x00,0x00,0x31,0x39,0x3F,0x3F,0x20,0x3C,0x3F,0x3E,0x00,0x00,
0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x14,0x00,0x00,0x00,0x00
};
unsigned char extrabytes[128];
unsigned char aPatchSndmon[]={0xa9,0x01,0x8d,0x0f,0xc0,0xa9,0x00,0x8d,0xc6,0x02,0x60};
unsigned char aPatchRckmon[]={0xa9,0x01,0x8d,0x0f,0xc0,0x4c,0x12,0xc0};
unsigned char aPatchPolly1[]={0xa9,0x7f,0x8d,0x0d,0xdc,0xad,0x0d,0xdc,0xa0,0x00,0xea};
unsigned char aPatchPolly2[]={0xa0,0x19,0xb9,0x47,0x0b,0x99,0xff,0xd3,0x88,0xd0,0xf7,0xa9,0x00,0x8d,0x15,0xd0,0xea,0xea,0xea,0xea,0xea,0xea};
unsigned char aPatchElcSnd[]={0x48,0x20,0x18,0x00,0x68,0xaa,0x8e,0xab,0x02,0xbd,0x15,0x00,0x8d,0xff,0x02,0xa9,0x01,0x8d,0xf9,0x02,0x60,0x0a};
unsigned char aPatchUbiksM[]={0x4C,0x00,0x00,0x4C,0x00,0x00,0x18,0x69,0x80,0x8D,0x00,0x00,0xA2,0x00,0xA9,0x00,0x9D,0x00,0xD4,0xE8,0xE0,0x20,0xD0,0xF6,0x60,0xA5,0x01,0x48,0xA9,0x36,0x85,0x01,0x20,0x00,0x00,0x68,0x85,0x01,0x60};
unsigned char aPatchMastCm[]={0xA9,0x01,0x8D,0x00,0x00,0xD0,0x21,0xA9,0x00,0xD0,0x31};
unsigned char aPatchPolyAn[]={0x78,0xD8,0xA2,0xFF,0x9A,0x20,0x5B,0x15,0x20,0x00,0x10,0x4C,0x58,0x15,0xAD,0x05,0x20,0xD0,0x0B,0xA2,0x02,0xBD,0x00,0x0D,0x95,0x00,0xE8,0xD0,0xF8,0x60,0xA2,0x02,0xBD,0x00,0x1A,0x95,0x00,0xE8,0xD0,0xF8,0x60};
unsigned char aPatchMssiah[]={0x78,0xA9,0x35,0x85,0x01,0x20,0x1C,0x5F,0x20,0xF3,0x5E,0xA9,0x00,0x8D,0x0E,0xDC,0x8D,0x0F,0xDC,0x8D,0x19,0xD0,0x8D,0x1A,0xD0,0xA9,0x7F,0x8D,0x0D,0xDC,0xA9,0x81,0x8D,0x0D,0xDC,0xA9,0x94,0x8D,0xFE,0xFF,0xA9,0x5F,0x8D,0xFF,0xFF,0xA9,0xA4,0x8D,0xFA,0xFF,0xA9,0x5F,0x8D,0xFB,0xFF,0xA9,0xF6,0x2C,0x5A,0x71,0x30,0x02,0xA9,0xAC,0x8D,0x04,0xDC,0xA9,0x07,0x8D,0x05,0xDC,0xA9,0x11,0x8D,0x0E,0xDC,0xA9,0x1B,0x8D,0x11,0xD0,0x58,0x20,0x95,0x5E,0x60,0,0,0,0,0};
unsigned char aPatchArneDD[]={0xa9,0x00,0xea,0xc9,0x01,0xf0,0x05};
unsigned char aPatchDMC4f9[]={0xC8,0xB1,0xF8,0x9D,0x26,0x17,0x60};
unsigned char aPatchDblTrk[]={0xA9,0x63,0x8D,0x04,0xDC,0xA9,0x26,0x8D,0x05,0xDC,0xA9,0x00,0x8D,0xEB,0x0F,0x4C,0x48,0x10,0xA9,0x00,0x29,0x01,0xAA,0xEE,0xEB,0x0F,0xBD,0xFB,0x0F,0x8D,0xF9,0x0F,0x4C,0x21,0x10,0x21,0x00,0x00,0x00,0x00};
char ids[30]="Generic";
unsigned char *p;
int fsiz,initaddr,playaddr,loadaddr,i,j,k,extra=0;
typedef struct {
    int offset;
    unsigned char checkbyte;
} AOF;
AOF af4[]=
{{0x006, 0xad},{0x015, 0xee},{0x018, 0xee},{0x01b, 0xee},{0x025, 0xce},{0x02d, 0x8d},{0x035, 0x8d},{0x039, 0xad},{0x04b, 0xde},{0x056, 0xbc},{0x065, 0x9d},{0x068, 0x9d},{0x06b, 0x9d},{0x06e, 0x8d},{0x077, 0x8d},{0x07e, 0xad}
,{0x083, 0x9d},{0x086, 0xfe},{0x08c, 0xad},{0x093, 0xad},{0x098, 0x9d},{0x09b, 0xfe},{0x0a1, 0xad},{0x0b2, 0x9d},{0x0b5, 0xbc},{0x0b8, 0x9d},{0x0bd, 0x9d},{0x0cc, 0x9d},{0x0cf, 0xfe},{0x0dc, 0x9d},{0x0ee, 0x9d},{0x0f6, 0x8d}
,{0x0f9, 0xfe},{0x102, 0x8d},{0x10b, 0xfe},{0x11f, 0x9d},{0x131, 0x9d},{0x13a, 0xbd},{0x13d, 0x9d},{0x143, 0x7d},{0x146, 0x9d},{0x151, 0xac},{0x157, 0x9d},{0x15a, 0x9d},{0x161, 0x9d},{0x164, 0xbd},{0x169, 0xbd},{0x170, 0x8e}
,{0x18c, 0x9d},{0x18f, 0x9d},{0x197, 0x9d},{0x19b, 0x9d},{0x1a3, 0x9d},{0x1a8, 0x9d},{0x1ac, 0x9d},{0x1af, 0xfe},{0x1b2, 0xbc},{0x1bd, 0x9d},{0x1c0, 0xbd},{0x1c5, 0xde},{0x1ca, 0xfe},{0x1d0, 0xfe},{0x1dd, 0xac},{0x1e0, 0xbd}
,{0x1e5, 0xbd},{0x1ea, 0x9d},{0x1ed, 0xbd},{0x1f7, 0x8d},{0x1fd, 0x8d},{0x203, 0x8d},{0x20a, 0xad},{0x211, 0xad},{0x21f, 0x9d},{0x225, 0x8d},{0x228, 0xbd},{0x22d, 0xde},{0x232, 0xfe},{0x237, 0xfe},{0x23a, 0xbd},{0x23d, 0xdd}
,{0x242, 0x9d},{0x245, 0xde},{0x248, 0xde},{0x24b, 0xbd},{0x256, 0x8d},{0x25f, 0x7d},{0x263, 0xce},{0x269, 0x6e},{0x26f, 0x8d},{0x275, 0x8d},{0x27b, 0x8d},{0x27e, 0xbd},{0x287, 0xad},{0x28a, 0xed},{0x28d, 0x8d},{0x290, 0xad}
,{0x293, 0xed},{0x296, 0x8d},{0x29c, 0xbd},{0x2a3, 0xbc},{0x2aa, 0xad},{0x2ad, 0x6d},{0x2b0, 0x8d},{0x2b3, 0xad},{0x2b6, 0x6d},{0x2b9, 0x8d},{0x2bf, 0xac},{0x2c2, 0xad},{0x2c8, 0xad},{0x2d0, 0xac},{0x2d3, 0xbd},{0x2d7, 0xfd}
,{0x2de, 0xbd},{0x2e9, 0xad},{0x2ed, 0xbd},{0x2f0, 0xed},{0x2f3, 0x9d},{0x2f9, 0xbd},{0x2fc, 0xed},{0x2ff, 0x9d},{0x308, 0xad},{0x30c, 0xbd},{0x30f, 0x6d},{0x312, 0x9d},{0x318, 0xbd},{0x31b, 0x6d},{0x31e, 0x9d},{0x324, 0xad}
,{0x334, 0xdd},{0x341, 0xdd},{0x34a, 0x8d},{0x350, 0xad},{0x355, 0x8d},{0x358, 0xbd},{0x35d, 0xbd},{0x361, 0xed},{0x364, 0x9d},{0x367, 0xbd},{0x36c, 0x9d},{0x375, 0x9d},{0x37a, 0xbd},{0x37e, 0x6d},{0x381, 0x9d},{0x384, 0xbd}
,{0x389, 0x9d},{0x392, 0x9d},{0x39a, 0xbd},{0x3a1, 0xbd},{0x3af, 0xac},{0x3b2, 0xbd},{0x3bb, 0xbd},{0x3c3, 0xad},{0x3cc, 0xbd},{0x3db, 0x9d},{0x3de, 0x8c},{0x3e1, 0xad},{0x3ea, 0x8e},{0x3f7, 0xbd},{0x41d, 0x8d},{0x420, 0xae}
,{0x424, 0x2d},{0x42b, 0x6d},{0x444, 0xbd},{0x44f, 0xcd},{0x458, 0x9d},{0x45e, 0xac},{0x461, 0xad},{0x468, 0xad},{0x488, 0xbd},{0x496, 0x99},{0x49c, 0x8d},{0x49f, 0xad},{0x4a8, 0xbd},{0x4ac, 0x6d},{0x4b2, 0xac},{0x4b5, 0xad}
,{0x4c6, 0xad},{0x4cf, 0xac},{0x4d2, 0xbd},{0x4e7, 0x9d},{0x4ed, 0xbd},{0x4f3, 0xbd},{0x4f9, 0xbd},{0x4fe, 0x9d},{0x501, 0xad},{0x508, 0xde},{0x50f, 0x9d},{0x514, 0xbd},{0x51f, 0xbd},{0x526, 0xac},{0x537, 0xac},{0x53a, 0xbd}
,{0x547, 0xad},{0x557, 0xad}
};
AOF af40[]=
{{0x5a7, 0x8d},{0x704, 0x9d},{0x70c, 0x8d},{0x711, 0x8d},{0x714, 0x8d},{0x717, 0x8d},{0x71c, 0x9d},{0x71f, 0x9d},{0x722, 0x9d},{0x725, 0x9d},{0x72b, 0x8d}
};
AOF af41[]=
{{0x569, 0x9d},{0x571, 0x8d},{0x576, 0x8d},{0x579, 0x8d},{0x57c, 0x8d},{0x581, 0x9d},{0x584, 0x9d},{0x587, 0x9d},{0x58a, 0x9d},{0x590, 0x8d},{0x5a7, 0x8d}
};
AOF sld0[]=
{{0x0034, 0x9d},{0x0037, 0x9d},{0x003a, 0x9d},{0x003d, 0x9d},{0x0040, 0x9d},{0x00a3, 0x8d},{0x00b8, 0x8d},{0x00cd, 0x8d},{0x017c, 0xad},{0x0182, 0xad}
,{0x0188, 0xad},{0x03d3, 0x9d},{0x03da, 0x7d},{0x03dd, 0x9d},{0x03e7, 0x9d},{0x03ea, 0xbd},{0x03ee, 0x7d},{0x03f1, 0x9d},{0x0418, 0x9d},{0x0420, 0x9d}
,{0x0436, 0xb9},{0x043d, 0xbe},{0x0456, 0x99},{0x045a, 0xb9},{0x045d, 0xd9},{0x0465, 0x79},{0x0472, 0xf9},
};

AOF *afall[2]={af40,af41};
AOF *af;
int afsize[3];

/*****************************************************************************/
int fixfc4stack(unsigned char *buffer,int lenbuff)
{
    int z=0;
    if(lenbuff<0x600)
    {
        return -1;
    }
    i=0;
    j=0;
    afsize[0]=sizeof(af40)/sizeof(*af40);
    afsize[1]=sizeof(af41)/sizeof(*af41);
    afsize[2]=sizeof(af4 )/sizeof(*af4 );
    // 1st check common bytes
    for(i=0;i<afsize[2];i++)
    {
        if(buffer[af4[i].offset]!=af4[i].checkbyte)
        {
            j=-1;
            break;
        }
    }
    // then determine subversion
    if(j!=-1)
    {
        for(z=0;z<2;z++)
        {
            j=z;
            af=afall[z];
            for(i=0;i<afsize[z];i++)
            {
                if(buffer[af[i].offset]!=af[i].checkbyte)
                {
                    // Zyron's hack doesn't have 05a7 offset
                    if((z==1)&&(i==afsize[z]-1))
                    {
                        break;
                    }
                    j=-1;
                    break;
                }
            }
            if(j!=-1)
            {
                break;
            }
        }
    }
    // now patch lda $0100 -> lda $0200
    if(j!=-1)
    {
        for(i=0;i<afsize[2];i++)
        {
            if(buffer[af4[i].offset+2]==0x1)
            {
                buffer[af4[i].offset+2]=0x2;
                j|=0x100;
            }
        }
        for(i=0;i<afsize[z];i++)
        {
            if((z==1)&&(i==afsize[z]-1))
            {
               break;
            }
            if(buffer[af[i].offset+2]==0x1)
            {
                buffer[af[i].offset+2]=0x2;
                j|=0x100;
            }
        }
    }
return j;
}
/*****************************************************************************/
int fixsklstack(unsigned char *buffer,int lenbuff)
{
    int z=0;
    if(lenbuff<0x600)
    {
        return -1;
    }
    i=0;
    j=0;
    z=sizeof(sld0)/sizeof(*sld0);
    for(i=0;i<z;i++)
    {
        if(buffer[sld0[i].offset]!=sld0[i].checkbyte)
        {
            j=-1;
            break;
        }
    }
    if(j!=-1)
    {
        for(i=0;i<z;i++)
        {
            if(buffer[sld0[i].offset+2]==0x1)
            {
                buffer[sld0[i].offset+2]=0x2;
                j|=0x100;
            }
        }
    }
return j;
}
/*****************************************************************************/
int AdjustJ(int x,int la)
{
    x=x+2-la;
    return x;
}
/*****************************************************************************/
int CheckJ(int x, int fs)
{
    return ((x<0)||(x>(fs-1)));
}
/*****************************************************************************/
void AdjFC(void)
{
    if((p[0x48]==0x20) && (p[0x49]==0xd0))
    {
        p[0x47]=0xea;
        p[0x48]=0xea;
        p[0x49]=0xea;
    }
}
/* FC 1000/1006 **************************************************************/
int Chk_FC(void)
{
    if(fsiz<0x200) return 0;
    if((p[0x02]==0x4c) &&
       (p[0x08]==0xad) &&
       (p[0x0f]==0xc9) &&
       ((*(unsigned int*)(p+0x0b)&0xfffff0ff)==0x07F000C9))
    {
        playaddr=initaddr+6;
        AdjFC();
        strcpy(ids,"FutureComposer");
        i=fixfc4stack(p+2,fsiz-2);
        if(i!=-1)
        {
            strcat(ids," 4.");
            strcat(ids,((i&1)?"1":"0"));
            if(i&0x100)
                strcat(ids," (fixed)");
        }
        return 1;
    }
    return 0;
}
/***** FC 1000/102a (MS) *****************************************************/
int Chk_FCAlt(void)
{
    if(fsiz<0x200) return 0;
    if((p[0x02]==0x4c) &&
       (p[0x03]==0x08) && /*(p[0x08]!=0xad) &&*/
       (p[0x2c]==0xee) &&
       (p[0x2d]==0x42) &&
       (p[0x2f]==0xee) &&
       (p[0x30]==0x43)
      )
    {
        playaddr=initaddr+0x2a;
        AdjFC();
        strcpy(ids,"FutureComposer");
        strcat(ids," (altered)");
        return 1;
    }
    return 0;
}
/***** MusicAss 1048/1021 ****************************************************/
int Chk_MusAss(void)
{
    if(fsiz<0x200) return 0;
    j=-1;
    for (i=2;i<0x25;i++)
    {
        if((*(unsigned int*)(p+i)==0x90CE00A2) &&
           (*(unsigned int*)(p+0x05+i)==0x26200C30) &&
           (*(unsigned int*)(p+0x31+i)==0x628D0F29))
        {
            j=i;
            break;
        }
    }
    if(j>=0)
    {
/***** DoubleTracker 1048/1021+1000 2x speed *********************************/
        if((p[2]==0xad) &&
           (p[3]==0xd2) &&
           (*(unsigned int*)(p+0x05)==0x00A205F0) &&
           (*(unsigned int*)(p+0x19)==0x02A205F0)
          )
        {
            psidh[P_TIMING  ]=1; // CIA timing
            k=(loadaddr>>8)-1;
            initaddr=((k<<8)|0xd8); // $0fd8
            playaddr=((k<<8)|0xea); // $0fea
            extrabytes[0]=initaddr&0xff;
            extrabytes[1]=initaddr>>8;
            extra=sizeof(aPatchDblTrk);
            memmove(extrabytes+2,aPatchDblTrk,extra);
            extrabytes[0x10]=k  ;
            extrabytes[0x13]=k+1;
            extrabytes[0x1b]=k  ;
            extrabytes[0x1e]=k  ;
            extrabytes[0x21]=k  ;
            extrabytes[0x24]=k+1;
            p[0]=0;
            p[1]=0;

            strcpy(ids,"DoubleTracker");
            return 1;
        }
        else
        {
            initaddr=loadaddr+0x48-0x23+i;
            playaddr=loadaddr+0x21-0x23+i;
            if( (p[2]==0x4c) &&
                (p[5]==0x4c) &&
                (*(unsigned short int*)(p+3)==initaddr) &&
                (*(unsigned short int*)(p+6)==playaddr) )
            {
                initaddr=loadaddr  ;
                playaddr=loadaddr+3;
            }
            strcpy(ids,"MusicAssembler");
            return 1;
        }
    }
    return 0;
}
/***** MusicMixer 1041/107a **************************************************/
int Chk_MusMix(void)
{
    if(fsiz<0x200) return 0;
    j=-1;
    for (i=2;i<0x2d;i++)
    {
        if(p[0x43-0x2b+i]==0xa9&&
           (*(unsigned int*)(p+0x4b-0x2b+i)==0x0F29D417) &&
           (*(unsigned int*)(p+0xD4-0x2b+i)==0x2030FAB1) &&
           (*(unsigned int*)(p+0x7b-0x2b+i)==0xCE00A260))
        {
            j=i;
            break;
        }
    }
    if(j>=0)
    {
        initaddr=loadaddr+0x41-0x2b+i;
        playaddr=loadaddr+0x7a-0x2b+i;
        if( (p[2]==0x4c) &&
            (p[5]==0x4c) &&
            (*(unsigned short int*)(p+3)==initaddr) &&
            (*(unsigned short int*)(p+6)==playaddr) )
        {
            initaddr=loadaddr  ;
            playaddr=loadaddr+3;
        }
        strcpy(ids,"MusicMixer");
        return 1;
    }
    return 0;
}
/***** GMC 18ea/14ea *********************************************************/
int Chk_GMC(void)
{
    if(fsiz<0x900) return 0;
    j=-1;
    for (i=2;i<0x18;i++)
    {
        if((*(unsigned int*)(p+0x0d0-0x16+i)==0x18FADDC3) &&
           (*(unsigned int*)(p+0x0e0-0x16+i)==0x47FBB470) &&
           (*(unsigned int*)(p+0x1a4-0x16+i)==0x0a0a0a0a))
        {
            j=i;
            break;
        }
    }
    if(j>=0)
    {
        initaddr=loadaddr+0x8ea-0x16+i;
        playaddr=loadaddr+0x4ea-0x16+i;
        strcpy(ids,"GMC/Superiors");
        return 1;
    }
    return 0;
}
/***** Bappalander 1000/1018 *************************************************/
int Chk_Bappalander(void)
{
    if(fsiz<0x400) return 0;
    if((*(unsigned int*)(p+0x002)==0x7DA200A9) &&
       (*(unsigned int*)(p+0x017)==0xCE60B185) &&
       (*(unsigned int*)(p+0x215)==0x0a0a0a0a))
    {
        initaddr=loadaddr      ;
        playaddr=loadaddr+0x18;
        strcpy(ids,"Bappalander");
        return 1;
    }
    if((p[2]==0x4c) &&
       (*(unsigned int*)(p+0x00c)==0xA9FA10CA) &&
       (*(unsigned int*)(p+0x084)==0xBDAAB0B1) &&
       (*(unsigned int*)(p+0x25a)==0x0a0a0a0a))
    {
        initaddr=loadaddr+3   ;
        playaddr=loadaddr+0   ;
        strcpy(ids,"Bappalander");
        strcat(ids,"/SpaceLab");
        return 1;
    }
    return 0;
}
/***** Trackplayer 1140/1287 *************************************************/
int Chk_TrkPl3(void)
{
    if(fsiz<0x500) return 0;
    if((*(unsigned int*)(p+0x142)==0x00A900A2) &&
       (*(unsigned int*)(p+0x148)==0x20E0E8D4) &&
       (*(unsigned int*)(p+0x289)==0xCA2000A2) &&
       (*(unsigned int*)(p+0x491)==0x0a0a0a0a))
    {
        initaddr=loadaddr+0x140;
        playaddr=loadaddr+0x287;
        strcpy(ids,"TrackPlayer");
        return 1;
    }
    return 0;
}
/***** Groovy bits 1003/1000 *************************************************/
int Chk_Groovy(void)
{
    if(fsiz<0x200) return 0;
    if((p[2]==0x4c) &&
       (*(unsigned int*)(p+0x005)==0x9D8A00A2) )
    {
        j=0;
        k=(p[4]<<8)+p[3]-loadaddr+2;
        if((*(unsigned int*)(p+k)&0xfffff0ff)==0xAD0330EE)
        {
            j=1;
        }
        else if((p[k     ]==0xe6)&&
                (p[k+0x02]==0xa5)&&
                (p[k+0x01]==p[k+0x03])&&
                (p[k+0x04]==0xc9))
        {
            j=2;
        }
        if(j>0)
        {
            initaddr=loadaddr+3;
            playaddr=loadaddr+0;
            sprintf(ids,"GroovyBits v%d",j);
            return 1;
        }
    }
    return 0;
}
/***** Parsec (LoS) 1003/1000 ************************************************/
int Chk_Parsec(void)
{
    if(fsiz<0x200) return 0;
    if((*(unsigned int*)(p+0x0d8)==0x06ADF4F2) &&
       (*(unsigned int*)(p+0x0e0)==0xD002C974) &&
       (*(unsigned int*)(p+0x0f4)==0x180A0A00) )
    {
        initaddr=loadaddr+3;
        playaddr=loadaddr+0;
        strcpy(ids,"Parsec/LoS");
        return 1;
    }
    if((*(unsigned int*)(p+0x0db)==0x06ADF4F2) &&
       (*(unsigned int*)(p+0x0e3)==0xD002C977) &&
       (*(unsigned int*)(p+0x0fa)==0x180A0A00) )
    {
        initaddr=loadaddr+3;
        playaddr=loadaddr+0;
        strcpy(ids,"Parsec/LoS");
        return 1;
    }
    return 0;
}
/***** Sosperec: TAX+1103/1100 ***********************************************/
int Chk_Sosperec(void)
{
    if(fsiz<0x200) return 0;
    if((*(unsigned int*)(p+0x010)==0x02020202) &&
      ((*(unsigned int*)(p+0x102)&0xff00ffff)==0x8E00AA4C) &&
       (*(unsigned int*)(p+0x132)==0xD4168ED4))
    {
        initaddr=loadaddr+0xfc;
        playaddr=loadaddr+0x100;
        p[0x0fe]=0xaa;
        p[0x0ff]=0x4c;
        p[0x100]=0x03;
        p[0x101]=(loadaddr+0x100)>>8;
        strcpy(ids,"Sosperec");
        return 1;
    }
    return 0;
}
/***** Soedesoft+hacks *******************************************************/
int Chk_SoedeSoft(void)
{
    if(fsiz<0x200) return 0;
    if(((*(unsigned int*)(p+0x02b)&0xfffff0ff)==0x3399A0A0) &&
        (*(unsigned int*)(p+0x02f)==0xFAD08803) &&
        (*(unsigned int*)(p+0x107)==(0x00DA2060|((loadaddr>>8)<<24))) )
    {
        if(p[2]==0x4c)
        {
            initaddr=loadaddr;
            p[3]=0x29;
            p[4]=loadaddr>>8;
        }
        else
            initaddr=loadaddr+0x29;

        playaddr=loadaddr+0x106;
        p[0xda]=0x60;
        if(p[0x142]==0xa9)/* end of irq d019/ea31 */
        {
            for(j=0x142;j<0x14a;j++)
                p[j]=0x60;
        }
        strcpy(ids,"Soedesoft");strcat(ids," v1");
        return 1;
    }
    if((p[2]==0x4c) &&
       (p[5]==0x4c) &&
       (p[8]==0x4c) &&
       (*(unsigned int*)(p+0x01a)==0x88033399) &&
       (*(unsigned int*)(p+0x01e)==0x00A9FAD0))
    {
        initaddr=loadaddr;
        if(p[0x6]==0x7b)
            playaddr=loadaddr+3;
        else if(p[0x9]==0x7b)
            playaddr=loadaddr+6;
        else
            playaddr=loadaddr+0x7b;
        p[0x5c]=0x60;
        strcpy(ids,"Soedesoft");strcat(ids," v2");
        return 1;
    }
    if((p[2]==0x4c) &&
       (p[5]==0x4c) &&
       (p[6]==0x35) &&
       (p[8]==0x4c) &&
       (p[9]==0x7c) &&
       (*(unsigned int*)(p+0x03b)==0x88033399) &&
       (*(unsigned int*)(p+0x07d)==0x037CEE60))
    {
        initaddr=loadaddr+3;
        playaddr=loadaddr+6;
        strcpy(ids,"Soedesoft");strcat(ids," v3");
        return 1;
    }
    return 0;
}
/***** Prosonix 1000/1009 ****************************************************/
int Chk_Prosonix1(void)
{
    if(fsiz<0x200) return 0;
    if((p[2]==0x4c) &&
       (p[5]==0x4c) &&
       (p[8]==0x4c) &&
      ((*(unsigned int*)(p+0x00b)&0x00ffffff)==0x00F000A9) &&
      ((*(unsigned int*)(p+0x00f)&0x00ff00ff)==0x00600010))
    {
        j=AdjustJ(p[3]|p[4]<<8,loadaddr);
        if( !CheckJ(j,fsiz) )
        {
            if((p[j+0x00]==0xa9) &&
               (p[j+0x01]==0x01) &&
               (p[j+0x02]==0x8d) &&
               (p[j+0x05]==0xa2) )
            {
                initaddr=loadaddr+0;
                playaddr=loadaddr+9;
                strcpy(ids,"Prosonix");strcat(ids," v1");
                return 1;
            }
        }
    }
    return 0;
}
/* 4 JMPS ********************************************************************/
int Chk_4JMPS(void)
{
    if(fsiz<0x800) return 0;
    if((p[0x2]==0x4c) &&
       (p[0x5]==0x4c) &&
       (p[0x8]==0x4c) &&
       (p[0xb]==0x4c))
    {
        j=AdjustJ(p[3]|p[4]<<8,loadaddr);
        if( !CheckJ(j,fsiz) )
        {
            if(*(unsigned int*)(p+j)==0x0C8D03A9)
            {
                j=AdjustJ(p[0xc]|p[0xd]<<8,loadaddr);
                if( !CheckJ(j,fsiz) )
                {
                    if((p[j+0]==0xad) &&
                       (p[j+1]==0x0c) &&
                       (p[j+3]==0xf0) &&
                       (p[j+8]==0x4c))
                    {
                        initaddr=loadaddr+0;
                        playaddr=loadaddr+9;
                        strcpy(ids,"Prosonix");strcat(ids," v2");
                        return 1;
                    }
                }
            }
/***** TFMX/Huelsbeck 1009/1000 **********************************************/
            if((p[j+0x00]==0xad)&&
               (p[j+0x03]==0x30)&&
               (p[j+0x05]==0x20))
            {
                j=AdjustJ(p[0xc]|p[0xd]<<8,loadaddr);
                if((p[j+0x00]==0x8d) &&
                   (p[j+0x03]==0x8e) &&
                   (p[j+0x06]==0x60) &&
                   ((p[j+0x07]==0x18) ||(p[j+0x0c]==0x18)) )
                {
                    initaddr=loadaddr+9;
                    playaddr=loadaddr+0;
                    strcpy(ids,"TFMX/Huelsbeck");
                    return 1;
                }
            }
/***** Heathcliff/DigitalArts 1009/1000 **************************************/
/***** "Forgot to give a name player Rene Lergner"****************************/
            if(((*(unsigned int*)(p+j+0   )&0xffff00ff)==0xFBF000A9)&&
               ((*(unsigned int*)(p+j+0x04)&0x00fff0ff)==0x008d00a9)&&
               ((*(unsigned int*)(p+j+0x09)&0x00ffffff)==0x002000a2)&&
               ((*(unsigned int*)(p+j+0x0e)&0x00ffffff)==0x002007a2)
              )
            {
                initaddr=loadaddr+9;
                playaddr=loadaddr+0;
                strcpy(ids,"Heathcliff");strcat(ids," v1");
                return 1;
            }
/***** DMC 4.x with patch at $0ff9 1000/1003 *********************************/
            k=loadaddr>>8;
            if(((*(unsigned int*)(p+2+0   )&0xff00ffff)==0x4C001d4c)&&
               ((*(unsigned int*)(p+2+0x04)&0xffff00ff)==0x2F4C0085)&&
               ((*(unsigned int*)(p+2+0xdf)&0xff00ffff)==0x4C00F920)&&
               (p[2+0xe1]==k-1)
              )
            {
                initaddr=loadaddr+0;
                playaddr=loadaddr+3;
                j=((k-1)<<8)|0xf9;
                extrabytes[0]=j&0xff;
                extrabytes[1]=j>>8;
                memmove(extrabytes+2,aPatchDMC4f9,sizeof(aPatchDMC4f9));
                extrabytes[2+5] = (k+7);
                extra=sizeof(aPatchDMC4f9);
                p[0]=extrabytes[2+5] = (k+7);
                p[1]=aPatchDMC4f9[sizeof(aPatchDMC4f9)-1];
                sprintf(ids,"DMC 4.x + patch @ $%02xf9",k-1);
                return 1;

            }
        }
    }
    return 0;
}
/***** Heathcliff/DigitalArts v3 1003/1000 ***********************************/
int Chk_Heathcliff(void)
{
    if(fsiz<0x800) return 0;
    if((p[0x2]==0x4c) &&
       (p[0x5]==0xa9) &&
       (p[0xa]==0xa2) )
    {
        j=AdjustJ(p[3]|p[4]<<8,loadaddr);
        if( !CheckJ(j,fsiz) )
        {
            if(((*(unsigned int*)(p+j+0   )&0x00ffffff)==0x00F015A9) &&
               ((*(unsigned int*)(p+j+0x04)&0x00ffffff)==0x002000a2)&&
               ((*(unsigned int*)(p+j+0x09)&0x00ffffff)==0x002007a2)
              )
            {
                initaddr=loadaddr+3;
                playaddr=loadaddr+0;
                strcpy(ids,"Heathcliff");strcat(ids," v3");
                return 1;
            }
        }
    }
    return 0;
}
/***** Prosonix v3 1000/1006 *************************************************/
int Chk_3JMPs1(void)
{
    if(fsiz<0x400) return 0;
    if((p[0x2]==0x4c) &&
       (p[0x5]==0x4c) &&
       (p[0x8]==0x4c) &&
       (p[0xb]!=0x4c))
    {
        j=AdjustJ(p[3]|p[4]<<8,loadaddr);
        if( !CheckJ(j,fsiz) )
        {
            if((*(unsigned short int*)(p+j)==0x03A9) &&(p[j+2]==0x8d))
            {
                k=p[j+3];
                j=AdjustJ(p[0x9]|p[0xa]<<8,loadaddr);
                if( !CheckJ(j,fsiz) )
                {
                    if((p[j+0]==0xad) &&
                       (p[j+1]==k   ) &&
                       (p[j+3]==0xf0) &&
                       (p[j+8]==0x4c))
                    {
                        initaddr=loadaddr+0;
                        playaddr=loadaddr+6;
                        strcpy(ids,"Prosonix");strcat(ids," v3");
                        return 1;
                    }
                }
            }
/***** Heathcliff/DigitalArts v2 1006/1000 ***********************************/
            if(((*(unsigned int*)(p+j+0   )&0x00ff00ff)==0x00F000A9) &&
               ((*(unsigned int*)(p+j+0x04)&0x00ffffff)==0x002000a2) &&
               ((*(unsigned int*)(p+j+0x09)&0x00ffffff)==0x002007a2)
              )
            {
                initaddr=loadaddr+6;
                playaddr=loadaddr+0;
                strcpy(ids,"Heathcliff");strcat(ids," v2");
                return 1;
            }
/***** Frank Hammer/Sharon 1000/1006 *****************************************/
            if( (*(unsigned short int*)(p + j) == 0x10AD) &&
                (p[j + 0x03] == 0x8d) &&
                (p[j + 0x32] == 0x60) &&
                (*(unsigned int*)(p + j + 0x33) == 0x18F003C0)
              )
            {
                initaddr = loadaddr + 0;
                playaddr = loadaddr + 6;
                strcpy(ids, "Frank Hammer");
                return 1;
            }
        }
    }
    return 0;
}
/***** Arne/AFL 1000/1009 ****************************************************/
int Chk_ArneAFL(void)
{
    if(fsiz<0x400) return 0;
    if((p[0x2]==0x4c) &&
       (p[0x5]==0x4c) &&
       (p[0x8]==0x4c) &&
       (p[0xb]==0x4c))
    {
        j=AdjustJ(p[3]|p[4]<<8,loadaddr);
        if( !CheckJ(j,fsiz) )
        {
            if(*(unsigned int*)(p+j)==0x40093F29)
            {
                j=AdjustJ(p[0xc]|p[0xd]<<8,loadaddr);
                if( !CheckJ(j,fsiz) )
                {
                    if((p[j+0]==0x2c) &&
                       (p[j+3]==0x30) &&
                       (p[j+5]==0x70) &&
                       (p[j+7]==0xa9))
                    {
                        initaddr=loadaddr+0;
                        playaddr=loadaddr+9;
                        strcpy(ids,"Arne/AFL");
                        k=0x5b;
                        if(*(unsigned int*)(p+k)==0xc9dd0ead)
                        {
                            memmove(p+k,aPatchArneDD,sizeof(aPatchArneDD));
                            strcat(ids," (fixed)");
                        }
                        return 1;
                    }
                }
            }
        }
    }
    return 0;
}
/***** Arne/SoundMaker v4 1000/1006 or 1020/1026 *****************************/
int Chk_ArneSndMk(void)
{
    if(fsiz<0x400) return 0;
    i=0;
    for(k=0;k<=0x20;k+=0x20)
    {
        if((p[2+k]==0x4c) &&
           (p[5+k]!=0x4c) &&
           (p[8+k]==0x4c) )
        {
            j=AdjustJ( p[9+k]|p[10+k]<<8,loadaddr);
            if( CheckJ(j,fsiz) )
            {
                break;
            }
            if((p[j  ]==0xad) &&
               (*(unsigned int*)(p+j+3)==0x60F001C9))
            {
                initaddr=loadaddr+k+0;
                playaddr=loadaddr+k+6;
                strcpy(ids,"SoundMaker");strcat(ids," v4/Arne");
                i=1;
                break;
            }
        }
    }
    return i;
}
/***** Digitalizer 2.x by Olav/PD 1003/1006 (normal version is 1000/1003) ****/
int Chk_Digitalizer(void)
{
    if(fsiz<0x200) return 0;
    if((p[2]==0x4c) &&
       (p[5]==0x4c) &&
       (p[8]==0x20) &&
       (*(unsigned int*)(p+0x0B)==0x10033DCE) &&
       (*(unsigned int*)(p+0x1B)==0xADFAD0CA))
    {
        initaddr=loadaddr+3;
        playaddr=loadaddr+6;
        strcpy(ids,"Digitalizer 2.x");
        return 1;
    }
    return 0;
}
/***** Soundmon c000/c020 + patch ********************************************/
int Chk_Soundmon(void)
{
    if((fsiz+loadaddr>0xcb00) &&
       (fsiz>0x2b00) &&
       (loadaddr<=0xa000) )
    {
        if((*(unsigned int*)(p+0xc000-loadaddr+2)==0x4cc0124c) &&
           (*(unsigned int*)(p+0xc020-loadaddr+2)==0xC58D01A5))
        {
            if( (*(unsigned int*)(p+0xc029-loadaddr+2)==0xADCBE120) )
            {
                initaddr=0xce30;
                playaddr=0;
                psidh[P_MARKER  ]='R';
                psidh[P_FREEPAGE]=8; // freepages
                psidh[P_FREEPMAX]=(loadaddr>>8)-8;
                sprintf(ids,"DUSAT/RockMon%s","3h");
            }
            else if( (*(unsigned int*)(p+0xc029-loadaddr+2)==0xAD80a020) )
            {
                initaddr=0xc000;
                playaddr=0;
                psidh[P_MARKER  ]='R';
                psidh[P_FREEPAGE]=8; // freepages
                psidh[P_FREEPMAX]=(loadaddr>>8)-8;
                j=initaddr-loadaddr+2;
                memmove(p+j,aPatchRckmon,sizeof(aPatchRckmon));
                sprintf(ids,"DUSAT/RockMon%s","2");
            }
            else
            {
                initaddr=0xc000;
                playaddr=0xc020;
                j=initaddr-loadaddr+2;
                memmove(p+j,aPatchSndmon,sizeof(aPatchSndmon));
                p[0xc031-loadaddr+2]=0x60;
                psidh[P_TIMING  ]=1; // CIA timing, not always needed
                psidh[P_FREEPAGE]=8; // freepages
                psidh[P_FREEPMAX]=(loadaddr>>8)-8;
                strcpy(ids,"SoundMonitor");
            }
            return 1;
        }
        if((*(unsigned int*)(p+0xc000-loadaddr+2)==0x4cc0124c) &&
           (*(unsigned int*)(p+0xc01d-loadaddr+2)==0x0E8E00a2))
        {
            if((*(unsigned int*)(p+0x9fd0-loadaddr+2)==0x018536a9) &&
               (*(unsigned int*)(p+0x9fdb-loadaddr+2)==0x8D9FA99F) )
            {
                initaddr=0x9fd0;
                playaddr=0;
                psidh[P_MARKER  ]='R';
                psidh[P_FREEPAGE]=8; // freepages
                psidh[P_FREEPMAX]=(loadaddr>>8)-8;
                j=0x9fe1-loadaddr+2;
                p[j++]=0x20; // some have this nopped, restored.
                p[j++]=0x12;
                p[j++]=0xc0;
                sprintf(ids,"DUSAT/RockMon%s","4");
                return 1;
            }
            if((*(unsigned int*)(p+0x9f00-loadaddr+2)==0x8D02C0AD) &&
               (*(unsigned int*)(p+0x9f04-loadaddr+2)==0x75209F0A) )
            {
                initaddr=0xc000;
                playaddr=0;
                j=initaddr-loadaddr+2;
                memmove(p+j,aPatchRckmon,sizeof(aPatchRckmon));
                psidh[P_MARKER  ]='R';
                psidh[P_FREEPAGE]=8; // freepages
                psidh[P_FREEPMAX]=(loadaddr>>8)-8;
                sprintf(ids,"DUSAT/RockMon%s","3");
                return 1;
            }
        }
        if((*(unsigned int*)(p+0xc000-loadaddr+2)==0x4cc0124c) &&
           (*(unsigned int*)(p+0xc020-loadaddr+2)==0x4CA90295))
        {
            initaddr=0xc000;
            playaddr=0;
            j=initaddr-loadaddr+2;
            memmove(p+j,aPatchRckmon,sizeof(aPatchRckmon));
            psidh[P_MARKER  ]='R';
            psidh[P_FREEPAGE]=8; // freepages
            psidh[P_FREEPMAX]=(loadaddr>>8)-8;
            sprintf(ids,"DUSAT/RockMon%s","5");
            return 1;
        }
        if((*(unsigned int*)(p+0xc000-loadaddr+2)==0x4cc0124c) &&
           (*(unsigned int*)(p+0xc01d-loadaddr+2)==0x589B0020) &&
           (*(unsigned int*)(p+0xc02c-loadaddr+2)==0xAD9BA020))
        {
            initaddr=0xc000;
            playaddr=0;
            j=initaddr-loadaddr+2;
            memmove(p+j,aPatchRckmon,sizeof(aPatchRckmon));
            psidh[P_MARKER  ]='R';
            psidh[P_FREEPAGE]=8; // freepages
            psidh[P_FREEPMAX]=(loadaddr>>8)-8;
            strcpy(ids,"MusicMaster 1.3/BB");
            return 1;
        }
        if((*(unsigned int*)(p+0xc000-loadaddr+2)==0x4cc0124c) &&
           (*(unsigned int*)(p+0xc01d-loadaddr+2)==0x589B0020) &&
           (*(unsigned int*)(p+0xc02c-loadaddr+2)==0xadc47820))
        {
            initaddr=0xc000;
            playaddr=0;
            j=initaddr-loadaddr+2;
            memmove(p+j,aPatchRckmon,sizeof(aPatchRckmon));
            psidh[P_MARKER  ]='R';
            psidh[P_FREEPAGE]=8; // freepages
            psidh[P_FREEPMAX]=(loadaddr>>8)-8;
            strcpy(ids,"BeatBox/KarlXII");
            return 1;
        }
        if((*(unsigned int*)(p+0xc000-loadaddr+2)==0x4cc0124c) &&
           (*(unsigned int*)(p+0xc025-loadaddr+2)==0x03148DD4) &&
           (*(unsigned int*)(p+0xcbdd-loadaddr+2)==0xAD9F0020))
        {
            initaddr=0xc000;
            playaddr=0;
            j=initaddr-loadaddr+2;
            memmove(p+j,aPatchRckmon,sizeof(aPatchRckmon));
            psidh[P_MARKER  ]='R';
            psidh[P_FREEPAGE]=8; // freepages
            psidh[P_FREEPMAX]=(loadaddr>>8)-8;
            strcpy(ids,"Digitronix");
            return 1;
        }
    }
    return 0;
}
/***** AMP 2.x 157e/14ce->1000/1003 ******************************************/
int Chk_AMP2(void)
{
    if(fsiz<0x600) return 0;
    if((*(unsigned int*)(p+0x0dc)==0x5F4B3827) &&
       (*(unsigned int*)(p+0x1A3)==0x5EDE04F0) &&
       (*(unsigned int*)(p+0x1e8)==0x4a4a4a4a) &&
       (*(unsigned int*)(p+0x224)==0x0a0a0a0a))
    {
        /* found mixed cases:
        internalplayer/init/play
        init/play/internalplayer
        init/play only
        Better replace the correct ones at 1000/1003
        fix: there are versions using init=$1568 others $157e
        */
        j=0;
        if((p[2+0x568]==0xad) &&
           (p[2+0x569]==0x09))
        {
            j=0x68;
        }
        else
        if ((p[2+0x57e]==0xa5) &&
            (p[2+0x588]==0xad) &&
            (p[2+0x589]==0x09))
        {
            j=0x7e;
        }
        if(j)
        {
            p[2]=0x4c;
            p[3]=j;
            p[4]=(loadaddr>>8)+5;
            p[5]=0x4c;
            p[6]=0xce;
            p[7]=(loadaddr>>8)+4;
            strcpy(ids,"AMP 2.x");
            return 1;
        }
    }
    return 0;
}
/***** FC 3.x ****************************************************************/
int Chk_FC3x(void)
{
    if(fsiz<0x200) return 0;
    if((*(unsigned int*)(p+0x08a)==0x7AA200A9) &&
       (*(unsigned int*)(p+0x0af)==0x8DF110CA) &&
       (*(unsigned int*)(p+0x15e)==0x16D0FFC9) &&
       (p[0x104]==0xAD))
    {
        playaddr=loadaddr+6;
        initaddr=loadaddr;
        if(p[0x10a]==0x07)
        {
            initaddr=loadaddr-2;
            extrabytes[0]=initaddr&0xff;
            extrabytes[1]=initaddr>>8;
            extra=2;
            p[0]=0xa9;
            p[1]=0x02;
        }
        /* fix pointers, found wrong ones */
        j=2;
        p[j++]=0x4c;
        p[j++]=0xb4;
        p[j++]=loadaddr>>8;
        j=8;
        p[j++]=0x4c;
        p[j++]=0x02;
        p[j++]=(loadaddr>>8)+1;
        strcpy(ids,"FutureComposer");
        strcat(ids," 3.x");
        return 1;
    }
    return 0;
}
/***** Deenen JTS/TC 110a/112c (patch at $1000) ******************************/
int Chk_MoN_JTS(void)
{
    if(fsiz<0x200) return 0;
    if((p[0x05]==0x4c) &&
       (p[0x06]==0x2c) &&
       (*(unsigned int*)(p+0xe2)==0x70A200A9)&&
       (*(unsigned int*)(p+0xe9)==0xA9FA10CA) )
    {
        initaddr=loadaddr+0;
        playaddr=loadaddr+3;
        p[2]=0x4c;
        p[3]=0x0a;
        p[4]=(loadaddr>>8)+1;
        strcpy(ids,"MoN/JTS");
        return 1;
    }
    return 0;
}
/***** 3 JMPs ****************************************************************/
int Chk_3JMPs2(void)
{
    if(fsiz<0x200) return 0;
    if((p[2]==0x4c) &&
       (p[5]==0x4c) &&
       (p[8]==0x4c))
    {
        j=AdjustJ( p[6]|p[7]<<8,loadaddr);
        if( !CheckJ(j,fsiz) )
        {
        /* SIDduzzit 2.07: TAX+1000/1003 *************************************/
            if((p[j+0x00]==0xa2) &&
               (p[j+0x02]==0x8e) &&
               (p[j+0x05]==0xbd) &&
               (*(unsigned int*)(p+j+0x30)==0xF0F07F29))
            {
                j=AdjustJ(p[3]|p[4]<<8,loadaddr);
                if( !CheckJ(j,fsiz) )
                {
                    if(p[j]!=0xaa)
                    {
                        initaddr=loadaddr-1;
                        extrabytes[0]=initaddr&0xff;
                        extra=1;
                        p[0]=initaddr>>8;
                        p[1]=0xaa;
                    }
                    sprintf(ids,"SidDuzzIt %s","2.07");
                    return 1;
                }
            }
        /* Anvil 1003/1006 ***************************************************/
            if ((p[j + 0x00] == 0xa9) &&
                (p[j + 0x01] == 0x01) &&
                (p[j + 0x02] == 0x8d) &&
                (p[j + 0x08] == 0x8d) &&
                (p[j + 0x0b] == 0xa9)    )
            {
                j = AdjustJ(p[9] | p[0xa] << 8, loadaddr);
                if (!CheckJ(j, fsiz))
                {
                    if(*(unsigned int*)(p + j - 4) == 0x60EE10CA)
                    {
                        initaddr = loadaddr + 3;
                        playaddr = loadaddr + 6;
                        strcpy(ids, "Anvil");
                        return 1;
                    }
                }
            }
        }
        j=AdjustJ( p[9]|p[0xa]<<8,loadaddr);
        if( !CheckJ(j,fsiz) )
        {
        /* Zardax 1000/1006 **************************************************/
            if((p[j+0x00]==0xad) &&
               (*(unsigned int*)(p+j+0x03)==0xCE6001F0) &&
               (*(unsigned int*)(p+j+0x0a)==0x2002A209))
            {
                initaddr=loadaddr;
                playaddr=loadaddr+6;
                strcpy(ids,"Zardax");strcat(ids," v1");
                return 1;
            }
            if((p[j+0x00]==0xad) &&
               (p[j-0x01]==0x60) &&
               (p[j+0x08]==0x8d) &&
               (p[j+0x0b]==0xa5) &&
               (*(unsigned int*)(p+j+0x03)==0xa56001F0))
            {
                initaddr=loadaddr;
                playaddr=loadaddr+6;
                strcpy(ids,"Zardax");strcat(ids," v2");
                return 1;
            }
        /* Deenen RWE Intro/TC 1000/1006 *************************************/
            if((p[j+0x00]==0xad) &&
               (p[j-0x01]==0x60) &&
               (*(unsigned int*)(p+j+0x03)==0x07f002c9) &&
               (*(unsigned int*)(p+j+0x08)==0x4c04d001))
            {
                initaddr=loadaddr;
                playaddr=loadaddr+6;
                strcpy(ids,"MoN/RWE");
                return 1;
            }
        /* Deenen Cyb2 1000/1006 *********************************************/
            if((p[j+0x00]==0xa9) &&
               (p[j+0x02]==0xf0) &&
               (p[j+0x04]==0x60) )
            {
                k=AdjustJ( p[3]|p[4]<<8,loadaddr);
                if( !CheckJ(k,fsiz) )
                {
                    if((((p[k+0x00]==0xa9)&&(p[k+0x02]==0x8d))||
                        ((p[k+0x00]==0xa2)&&(p[k+0x02]==0x8e)))&&
                       (p[k+0x01]==0x01)&&
                       (*(unsigned short int*)(p+k+3)==(unsigned short)((loadaddr+j-1)&0xffff)) )
                    {
                       initaddr=loadaddr;
                       playaddr=loadaddr+6;
                       strcpy(ids,"MoN/Cyb2");
                       return 1;
                    }
                }
            }
        /* Laxity v4 1000/1006 ***********************************************/
            if((p[j+0x00]==0xad) &&
               (p[j-0x01]==0x60) &&
               (p[j-0x0f]==0x8d) &&
               (p[j-0x3e]==0xa2) &&
               (*(unsigned int*)(p+j+0x03)==0xa26001d0))
            {
                initaddr=loadaddr;
                playaddr=loadaddr+6;
                p[2]=0x4c;
                i=(j-0x3e -2 + loadaddr);
                p[3]=i&0xff;
                p[4]=i>>8;
                strcpy(ids,"Laxity");strcat(ids," v4");
                return 1;
            }
        /* Roland Hermans special case 1006/1000 *****************************/
            if( (p[j+0x03]==0x8d) &&
                (p[j+0x12]==0x8d) &&
                (*(unsigned int*)(p+j+0x06)==0x690a0a0a) &&
                (*(unsigned int*)(p+j+0x28)==0xA9D4178D))
            {
                initaddr=loadaddr+6;
                playaddr=loadaddr;
                strcpy(ids,"Roland Hermans");
                return 1;
            }
        }
        /* SIDduzzit 0.98: TAX+1000/1003 *************************************/
        j=AdjustJ( p[3]|p[4]<<8,loadaddr);
        if( !CheckJ(j,fsiz) )
        {
            if((p[j+0x00]==0xbd) &&
               (p[j+0x03]==0x8d) &&
               (p[j+0x06]==0x8d) &&
               (p[j+0x09]==0xbd) )
            {
                initaddr=loadaddr-1;
                extrabytes[0]=initaddr&0xff;
                extra=1;
                p[0]=initaddr>>8;
                p[1]=0xaa;
                sprintf(ids,"SidDuzzIt %s","0.98");
                return 1;
            }
        /* Laxity v1 1000/1006 ***********************************************/
            if((*(unsigned int*)(p+j+0x00)==0xA98A00A2) &&
               (*(unsigned int*)(p+j+0x1b)==0xE49003E0))
            {
                initaddr=loadaddr+0;
                playaddr=loadaddr+6;
                strcpy(ids,"Laxity");strcat(ids," v1");
                return 1;
            }
        /* Deenen special case 1006/1000 *************************************/
            if(((*(unsigned int*)(p+j+0x00)&0xffff00ff)==0x013000A9)&&
               (p[j+0x04]==0x60)&&
               (p[j+0x05]==0xad)&&
               (p[j+0x08]==0xf0))
            {
                initaddr=loadaddr+6;
                playaddr=loadaddr+0;
                strcpy(ids,"Deenen");
                return 1;
            }
        }
        /* JO v1, variable 3/4 jmps ******************************************/
        for(i=2,k=0;i<=2+(4*3);i+=3)
        {
            if(p[i]==0x4c)
            {
                j=AdjustJ( p[i+1]|p[i+2]<<8,loadaddr);
                if( CheckJ(j,fsiz) )
                {
                    continue;
                }
                if( (p[j+0x00]==0xbd) &&
                    (p[j+0x03]==0x8d) &&
                    (p[j+0x06]==0xbd) &&
                    (p[j+0x09]==0x8d) )
                {
                    k|=1;
                    initaddr=loadaddr+i-2;
                }
                else if( (p[j+0x00]==0xa9) &&
                         (p[j+0x02]==0xd0) &&
                         (p[j+0x03]==0x01) &&
                         (p[j+0x04]==0x60) )
                {
                    k|=2;
                    playaddr=loadaddr+i-2;
                }
            }
        }
        if(k!=3)
        {
            initaddr=loadaddr;
            playaddr=initaddr+3;
        }
        else
        {
            /* add TAX */
            if(initaddr==loadaddr)
            {
                initaddr--;
                extrabytes[0]=initaddr&0xff;
                extra=1;
                p[0]=initaddr>>8;
                p[1]=0xaa;
            }
            else
            {
                extra=4;
                extrabytes[0]=(loadaddr-extra)&0xff;
                extrabytes[1]=(loadaddr-extra)>>8;
                extrabytes[2]=0xaa;
                extrabytes[3]=0x4c;
                p[0]=initaddr&0xff;
                p[1]=initaddr>>8;
                initaddr=loadaddr-extra;
            }
            strcpy(ids,"JO/Vibrants");strcat(ids," v1");
            return 1;
        }
    }
    return 0;
}
/***** JO v2, variable 1/3 JMPs but 1st if present is IRQ install ************/
int Chk_JOv2(void)
{
    if(fsiz<0x200) return 0;
    for(i=2,k=0;i<=2+(2*3);i+=3)
    {
        if(p[i]==0x4c)
        {
            j=AdjustJ( p[i+1]|p[i+2]<<8,loadaddr);
            if( CheckJ(j,fsiz) )
            {
                continue;
            }
            if( (p[j+0x00]==0x8d) &&
                (p[j+0x03]==0x8d) &&
                (*(unsigned int*)(p+j+0x06)==0xA9A80A0A))
            {
                k|=1;
                initaddr=loadaddr+i-2;
                break;
            }
            else if((p[j+0x00]==0x8d) &&
                    (*(unsigned int*)(p+j+0x03)==0xA9A80A0A))
            {
                k|=1;
                initaddr=loadaddr+i-2;
                break;
            }
        }
    }
    if( k )
    {
        for(j=0;j<0x10;j++)
        {
            if( (p[i+j+0x03]==0xad) &&
                (p[i+j+0x06]==0xc9) &&
                (p[i+j+0x07]==0x01) &&
                (p[i+j+0x08]==0xf0) &&
                (p[i+j+0x0a]==0xc9) )
            {
                k|=2;
                playaddr=initaddr+3;
                break;
            }
        }
    }
    if(k!=3)
    {
        initaddr=loadaddr;
        playaddr=initaddr+3;
    }
    else
    {
        strcpy(ids,"JO/Vibrants");strcat(ids," v2");
        return 1;
    }
    return 0;
}
/***** 2 JMPs ****************************************************************/
int Chk_2JMPs(void)
{
    if(fsiz<0x200) return 0;
    if((p[2]==0x4c) &&
       (p[5]==0x4c) )
    {
        j=AdjustJ( p[6]|p[7]<<8,loadaddr);
        if( !CheckJ(j,fsiz) )
        {
        /* XTracker_V4.x 1003/1000 *******************************************/
            if((p[j+0x00]==0xaa) &&
               (p[j+0x01]==0xbd) &&
               (p[j+0x04]==0x8d) )
            {
                initaddr=loadaddr+3;
                playaddr=loadaddr+0;
                sprintf(ids,"XTracker_V4.1%s/LoS","c");
                return 1;
            }
        /* Nordicbeat: TAX+1000/1003 *****************************************/
            if((p[j+0x00]==0xa2) &&
               (p[j+0x01]==0x00) &&
               (p[j+0x02]==0xce) &&
               (p[j+0x05]==0x30) &&
               (p[j+0x06]==0x09) &&
               (p[j+0x07]==0x20) &&
               (p[j+0x0a]==0x20) &&
               (p[j+0x0d]==0x4c) )
            {
                initaddr=loadaddr+6;
                playaddr=loadaddr+3;
                k=8;
                p[k++]=0xaa;
                p[k++]=0x4c;
                p[k++]=loadaddr&0xff;
                p[k++]=loadaddr>>8;
                strcpy(ids,"NordicBeat");
                return 1;
            }
        /* ICC/The Voice $1003/$1000 *****************************************/
            if((*(unsigned int*)(p+j+0x00)==0x00A918A2)&&
               (*(unsigned int*)(p+j+0x04)==0xCAD4009D)&&
               (*(unsigned int*)(p+j+0x43)==0x06F0F029)&&
               (*(unsigned int*)(p+j+0x53)==0x06F0F029)&&
               (*(unsigned int*)(p+j+0xa9)==0x4A4A4A4A))
            {
                initaddr=loadaddr+3;
                playaddr=loadaddr+0;
                strcpy(ids,"ICC/The Voice");
                return 1;
            }
        /* Bernhard Burgstaller 1003/1000 ************************************/
            if((*(unsigned int*)(p+j-0x01)==0x8d00a960)&&
               (*(unsigned int*)(p+j+0x07)==0xA2D4188D)&&
               (p[j+0x0c]==0x20)&&
               (p[j+0x0f]==0x20))
            {
                initaddr=loadaddr+3;
                playaddr=loadaddr+0;
                strcpy(ids,"Burgstaller");strcat(ids," v1");
                return 1;
            }
            if((*(unsigned int*)(p+j+0x00)==0x00A917A2)&&
               (*(unsigned int*)(p+j+0x04)==0xCAD4009D)&&
               (*(unsigned int*)(p+j+0x0f)==0xA2D4188D)&&
               (p[j+0x14]==0x20)&&
               (p[j+0x17]==0x20))
            {
                initaddr=loadaddr+3;
                playaddr=loadaddr+0;
                strcpy(ids,"Burgstaller");strcat(ids," v2");
                return 1;
            }
            if((p[j     ]==0x8d)&&
               (p[j+0x03]==0xa2)&&
               (p[j+0x04]==0x00)&&
               (p[j+0x05]==0x20)&&
               (p[j+0x08]==0x20)&&
               ((*(unsigned int*)(p+j+0x10)==0x00690A8A)||
                (*(unsigned int*)(p+j+0x16)==0x00690A8A))
              )
            {
                initaddr=loadaddr+3;
                playaddr=loadaddr+0;
                strcpy(ids,"Burgstaller");strcat(ids," v3");
                return 1;
            }
            if((p[j     ]==0x8d)&&
               (*(unsigned int*)(p+j+0x05)==0xA2D4188D)&&
               (p[j+0x09]==0x00)&&
               (p[j+0x0a]==0x20)&&
               (p[j+0x0d]==0x20)&&
               (*(unsigned int*)(p+j+0x1b)==0x00690A8A)
              )
            {
                initaddr=loadaddr+3;
                playaddr=loadaddr+0;
                strcpy(ids,"Burgstaller");strcat(ids," v4");
                return 1;
            }
        }
        j=AdjustJ( p[3]|p[4]<<8,loadaddr);
        if( !CheckJ(j,fsiz) )
        {
        /* XTracker_V4.x 1003/1000 *******************************************/
            if((p[j+0x00]==0xa0) &&
               (p[j+0x01]==0x00) &&
               (p[j+0x02]==0xf0) &&
               (p[j+0x04]==0x60) )
            {
                initaddr=loadaddr+3;
                playaddr=loadaddr+0;
                sprintf(ids,"XTracker_V4.1%s/LoS","a");
                return 1;
            }
            if((p[j+0x00]==0xce) &&
               (p[j+0x02]==(loadaddr>>8)) &&
               (p[j+0x03]==0x10) )
            {
                initaddr=loadaddr+3;
                playaddr=loadaddr+0;
                sprintf(ids,"XTracker_V4.1%s/LoS","b");
                return 1;
            }
            if((p[j+0x00]==0x2c) &&
               (p[j+0x02]==(loadaddr>>8)) &&
               (p[j+0x03]==0x30) &&
               (*(unsigned int*)(p+j+5)==0xA2600170))
            {
                initaddr=loadaddr+3;
                playaddr=loadaddr+0;
                strcpy(ids,"LordsOfSonics/MS");
                return 1;
            }
        /* Guy Shavitt 1000/1006 *********************************************/
            if((p[j+0x00]==0xa2) &&
               (p[j+0x01]==0x00) &&
               (p[0x08  ]==0xad) &&
               (p[0x0b  ]==0x10))
            {
                initaddr=loadaddr+0;
                playaddr=loadaddr+6;
                strcpy(ids,"Guy Shavitt");
                return 1;
            }
        /* Audial Arts: TAY+1000/1003 ****************************************/
            if((*(unsigned int*)(p+j+0x00)==0x00A978A2) &&
               (*(unsigned int*)(p+j+0x07)==0x20FA10CA) &&
               (*(unsigned int*)(p+j+0x21)==0xA9F710CA) &&
               (p[j+0x0d ]==0xb9) )
            {
                initaddr=loadaddr-1;
                extrabytes[0]=initaddr&0xff;
                extra=1;
                p[0]=initaddr>>8;
                p[1]=0xa8;
                strcpy(ids,"Audial Arts");
                return 1;
            }
        /* TFMX/MasterComposer 1003/1000 *************************************/
            if((*(unsigned int*)(p+j-0x03)==0xAD60FA10) &&
               (*(unsigned int*)(p+j+0x03)==0x0EAE12F0) &&
               (*(unsigned int*)(p+j+0x0e)==0x8EE8FA10) )
            {
                initaddr=loadaddr+3;
                playaddr=loadaddr+0;
                strcpy(ids,"TFMX/MasterComposer");
                return 1;
            }
        /* SIDduzzit 2.1: TAX+1000/1003 **************************************/
            if((p[j+0x00]==0xbd) &&
               (p[j+0x03]==0x8d) &&
               (p[j+0x06]==0xa9) &&
               (p[j+0x08]==0x8d) &&
               ((p[j+0x18]==0x4a)||(p[j+0x18]==0xa9))
              )
            {
                initaddr=loadaddr-1;
                extrabytes[0]=initaddr&0xff;
                extra=1;
                p[0]=initaddr>>8;
                p[1]=0xaa;
                sprintf(ids,"SidDuzzIt %s","2.1");
                return 1;
            }
        }
        /* Laxity v3 1000/1006 ***********************************************/
        if((p[8]==0x2c) &&
           (*(unsigned int*)(p+0xb)==0xA9600130) )
        {
            initaddr=loadaddr+0;
            playaddr=loadaddr+6;
            strcpy(ids,"Laxity");strcat(ids," v3");
            return 1;
        }
        /***** SidFactory II/Laxity: $1000/$1006-1009 ************************/
        if((p[0x08]==0xa9) &&
           (p[0x09]==0x00) &&
           (p[0x0a]==0x2c) &&
           (p[0x11]==0xa2) &&
           ( (*(unsigned int*)(p+0x0d) == 0x38704430) ||
             (*(unsigned int*)(p+0x0d) == 0x3e704A30) ||
             (*(unsigned int*)(p+0x0d) == 0x3a704630) ||
             (*(unsigned int*)(p+0x0d) == 0x4A705630) ||
             (*(unsigned int*)(p+0x0d) == 0x30703c30) )
          )
        {
            initaddr=loadaddr+0;
            playaddr=loadaddr+6;
            strcpy(ids,"SidFactory");strcat(ids, " II");strcat(ids, " v1");
            return 1;
        }
        if((p[0x0b]==0xa9) &&
           (p[0x0c]==0x00) &&
           (p[0x0d]==0x2c) &&
           (p[0x14]==0xa2) &&
           ( (*(unsigned int*)(p+0x10) == 0x38704430) ||
             (*(unsigned int*)(p+0x10) == 0x46705230) ||
             (*(unsigned int*)(p+0x10) == 0x49705530) )
          )
        {
            initaddr=loadaddr+0;
            playaddr=loadaddr+9;
            strcpy(ids,"SidFactory");strcat(ids, " II");strcat(ids, " v2");
            return 1;
        }
        if((p[0x08]==0xa9) &&
           (p[0x09]==0x00) &&
           (p[0x0a]==0x24) &&
           ( (*(unsigned int*)(p+0x0c) == 0x1c702830) ||
             (*(unsigned int*)(p+0x0c) == 0x1A702630) )
          )
        {
            initaddr=loadaddr+0;
            playaddr=loadaddr+6;
            strcpy(ids,"SidFactory");strcat(ids, " II");strcat(ids, " v3");
            return 1;
        }
        if((p[0x0b]==0xa9) &&
           (p[0x0c]==0x00) &&
           (p[0x0d]==0x8d) &&
           (p[0x10]==0x2c) &&
           (p[0x17]==0xa2) &&
           (*(unsigned int*)(p+0x13) == 0x38704430)
          )
        {
            initaddr=loadaddr+0;
            playaddr=loadaddr+9;
            strcpy(ids,"SidFactory");strcat(ids, " II");strcat(ids, " v4");
            return 1;
        }
    }
    return 0;
}
/***** Laxity v2 1000/1006 ***************************************************/
int Chk_LaxityV2(void)
{
    if(fsiz<0x200) return 0;
    for(k=0;k<=0x100;k+=0x100)
    {
        if((p[2+k]==0x4c) &&
           (p[5+k]==0x4c) &&
           (*(unsigned int*)(p+0xa+k)==0x2CD4188D) )
        {
            initaddr=loadaddr+0+k;
            playaddr=loadaddr+6+k;
            strcpy(ids,"Laxity");strcat(ids," v2");
            return 1;
        }
    }
    return 0;
}
/***** Rob Hubbard 1000/1012 *************************************************/
int Chk_HubbardV2(void)
{
    if(fsiz<0x200) return 0;
    i=0;
    if((p[0x02]==0x4c) &&
       (p[0x05]==0x4c) &&
       (p[0x08]==0x4c) &&
       (p[0x0b]==0x4c) &&
       (p[0x0e]==0x4c) &&
       (p[0x11]==0x4c) )
    {
        for(j=0x14;j<0x30;j++)
        {
            if((p[0+j]==0x2c) &&
               (p[3+j]==0x30) &&
               (p[5+j]==0x50))
            {
                initaddr=loadaddr+0;
                playaddr=loadaddr+0x12;
                strcpy(ids,"Hubbard");strcat(ids," v2");
                i=1;
                break;
            }
        }
    }
    return i;
}
/***** Rob Hubbard 1000/1006 *************************************************/
int Chk_HubbardV1(void)
{
    if(fsiz<0x200) return 0;
    i=0;
    for(k=0;k<=0x100;k++)
    {
        if((p[0x02+k]==0x4c) &&
           (p[0x05+k]==0x4c) )
        {
            for(j=k+8;j<k+0x20;j++)
            {
                if(p[0+j]==0x60)
                    break;
                if((p[0+j]==0x2c) &&
                   (p[3+j]==0x30) &&
                   (p[5+j]==0x50))
                {
                    initaddr=loadaddr+0+k;
                    playaddr=loadaddr+6+k;
                    strcpy(ids,"Hubbard");strcat(ids," v1");
                    i=1;
                    break;
                }
            }
        }
    }
    return i;
}
/***** Rob Hubbard 155f/103f (ACE_II hacks) **********************************/
int Chk_HubbardV3(void)
{
    if(fsiz<0x600) return 0;
    if((p[0x41]==0xa9) &&
       (p[0x46]==0x2c) &&
       (p[0x561]==0xa9) &&
       (p[0x562]==0x40) &&
       (p[0x566]==0x60) &&
       (*(unsigned int*)(p+0x49)==0x40502A30)&&
       (*(unsigned int*)(p+0x55)==0x9DD40499))
    {
        initaddr=loadaddr+0x55f;
        playaddr=loadaddr+0x3f;
        strcpy(ids,"Hubbard");strcat(ids," v3");
        return 1;
    }
    return 0;
}
/***** Rob Hubbard 1xxx/1xxx (simpler version of v5) *************************/
int Chk_HubbardV4(void)
{
    if(fsiz<0x700) return 0;
    i=0;
    for(k=0;k<=0x100;k++)
    {
        if((p[0x00 + k]==0xa2) &&
           (p[0x01 + k]==0x02) &&
           (p[0x02 + k]==0xce) &&
           (p[0x05 + k]==0x10) &&
           (p[0x06 + k]==0x06) &&
           (p[0x07 + k]==0xad) &&
           (p[0x2b + k]==0x30) &&
           (p[0x2d + k]==0x4c) &&
           (p[0x30 + k]==0x4c) )
        {
            i=k;
            break;
        }
    }
    if(i>0)
    {
        // play addr
        j=AdjustJ( p[k+3]|p[k+4]<<8,loadaddr);
        if( !CheckJ(j,fsiz) )
        {
            j-=0xf0;
            for(k=0;k<=0x100;k++)
            {
                if((p[j+k+0x00]==0xad)&&
                   (p[j+k+0x03]==0xd0)&&
                   (((p[j+k+0x05]==0xee)&&(p[j+k+0x08]==0xee))||
                    ((p[j+k+0x05]==0xe6)&&(p[j+k+0x07]==0xe6)))
                    )
                {
                    playaddr=loadaddr+j+k-2;
                    break;
                }
            }
            // init
            for(   ;k<=0x100;k++)
            {
                if((p[j+k+0x00]==0xaa)&&
                   (p[j+k+0x01]==0xbd)&&
                   (p[j+k+0x06]==0xbd)&&
                   (p[j+k+0x04]==0x85)&&
                   (p[j+k+0x09]==0x85)&&
                   (p[j+k+0x18]==0xa2))
                {
                    initaddr=loadaddr+j+k-2;
                    break;
                }
            }
            if(k==0x101)
            {
                initaddr=loadaddr;
                playaddr=initaddr+3;
                return 0;
            }
            else
            {
                if(i>=6)
                {
                    k=2;
                    p[k++]=0x4c;
                    p[k++]=initaddr&0xff;
                    p[k++]=initaddr>>8;
                    p[k++]=0x4c;
                    p[k++]=playaddr&0xff;
                    p[k++]=playaddr>>8;
                    initaddr=loadaddr;
                    playaddr=initaddr+3;
                }
                strcpy(ids,"Hubbard");strcat(ids," v4");
                return 1;
            }
        }
    }
    return 0;
}
/***** Rob Hubbard 1xxx/1xxx (FC probably based on this) *********************/
int Chk_HubbardV5(void)
{
    if(fsiz<0x700) return 0;
    i=0;
    for(k=0;k<=0x100;k++)
    {
        if((p[0x00 + k]==0xa2) &&
           (p[0x01 + k]==0x02) &&
           (p[0x02 + k]==0xce) &&
           (p[0x05 + k]==0x10) &&
           (p[0x06 + k]==0x06) &&
           (p[0x07 + k]==0xad) &&
           (p[0x2e + k]==0x30) &&
           (p[0x30 + k]==0x4c) &&
           (p[0x33 + k]==0x4c) )
        {
            i=k;
            break;
        }
    }
    if(i>0)
    {
        // play addr
        j=AdjustJ( p[k+3]|p[k+4]<<8,loadaddr);
        if( !CheckJ(j,fsiz) )
        {
            j-=0xf0;
            for(k=0;k<=0x100;k++)
            {
                if((p[j+k+0x00]==0xad)&&
                   (p[j+k+0x03]==0xc9)&&
                   (p[j+k+0x07]==0xc9)&&
                   (p[j+k+0x0b]==0xee)&&
                   (p[j+k+0x0e]==0xee)&&
                   (p[j+k+0x11]==0xee)
                    )
                {
                    playaddr=loadaddr+j+k-2;
                    break;
                }
            }
            // init
            for(   ;k<=0x100;k++)
            {
                if((p[j+k+0x00]==0x48)&&
                   (p[j+k+0x01]==0xa9)&&
                   (p[j+k+0x02]==0x01)&&
                   (p[j+k+0x03]==0x8d)&&
                   (p[j+k+0x07]==0xaa)&&
                   (p[j+k+0x0b]==0x85)&&
                   (p[j+k+0x1f]==0xa2))
                {
                    initaddr=loadaddr+j+k-2;
                    break;
                }
            }
            if(k==0x101)
            {
                initaddr=loadaddr;
                playaddr=initaddr+3;
                return 0;
            }
            else
            {
                if(i>=6)
                {
                    k=2;
                    p[k++]=0x4c;
                    p[k++]=initaddr&0xff;
                    p[k++]=initaddr>>8;
                    p[k++]=0x4c;
                    p[k++]=playaddr&0xff;
                    p[k++]=playaddr>>8;
                    initaddr=loadaddr;
                    playaddr=initaddr+3;
                }
                strcpy(ids,"Hubbard");strcat(ids," v5");
                return 1;
            }
        }
    }
    return 0;
}
/***** Mike/LSD 1006/1003 ****************************************************/
int Chk_MikeLSD(void)
{
    if(fsiz<0x200) return 0;
    if((p[0x02]==0x4c) &&
       (p[0x05]==0x4c) &&
       (p[0x08]==0x4c) &&
       (p[0x0b]==0x4c) &&
       (p[0x0e]==0x4c) &&
       (*(unsigned int*)(p+0x15)==0xA90001C9)&&
       (*(unsigned int*)(p+0x61)==0x07E93898))
    {
        initaddr=loadaddr+6;
        playaddr=loadaddr+3;
        strcpy(ids,"Mike/LSD");strcat(ids," v1");
        return 1;
    }
    if((p[0x02]==0x4c) &&
       (p[0x05]==0x4c) &&
       (p[0x08]==0xa9) &&
       (p[0x0b]==0x4c) &&
       (p[0x11]==0x4c) &&
       (*(unsigned int*)(p+0x14)==0xA96080A9)&&
       (*(unsigned int*)(p+0xfe)==0x07E9388A))
    {
        initaddr=loadaddr+6;
        playaddr=loadaddr+3;
        strcpy(ids,"Mike/LSD");strcat(ids," v2");
        return 1;
    }
    return 0;
}
/***** Comptech 1003/1000 ****************************************************/
int Chk_Comptech(void)
{
    if(fsiz<0x200) return 0;
    if((p[2]==0x4c) &&
       (p[5]==0x8d) &&
       (p[8]==0x60) )
    {
        j=AdjustJ(p[3]|p[4]<<8,loadaddr);
        if( !CheckJ(j,fsiz) )
        {
            if((p[j]==0xad) &&
               (*(unsigned int*)(p+j+0x3)==0xF6F0FFC9))
            {
                initaddr=loadaddr+3;
                playaddr=loadaddr+0;
                strcpy(ids,"Comptech 2.x/LoS");
                return 1;
            }
        }
    }
    return 0;
}
/***** SoundMaker v3 & 5_Dimension 1000/1006 *********************************/
int Chk_SoundMaker(void)
{
    if(fsiz<0x200) return 0;
    if((p[2]==0x4c) &&
       (p[5]!=0x4c) &&
       (p[8]==0x4c) )
    {
        j=AdjustJ(p[3]|p[4]<<8,loadaddr);
        if( !CheckJ(j,fsiz) )
        {
            if((p[j  ]==0xaa) &&
               (p[j+1]==0xbd) &&
               (p[j+4]==0x8d) &&
               (p[j+7]==0x8a) )
            {
                initaddr=loadaddr+0;
                playaddr=loadaddr+6;
                strcpy(ids,"SoundMaker");strcat(ids," v3/UA");
                return 1;
            }
        }
    }
    return 0;
}
/***** Electrosound **********************************************************/
int Chk_Electrosound(void)
{
    if(fsiz<0xc00) return 0;
    if((*(unsigned int*)(p+0x02 )==0x05D0B0C9) &&
       (*(unsigned int*)(p+0x06 )==0x154C30A9) &&
       (*(unsigned int*)(p+0x18a)==0x0a0a0a0a))
    {
        memset(p+0xa8a,0,0x278);
        p[0xa64]=0x60;
        p[0xa7d]=0x60;
        p[0xa86]=0x60;
        k=0xb02;
        memmove(p+k,aPatchElcSnd,sizeof(aPatchElcSnd));
        p[0xb05]=(loadaddr>>8)+5;
        p[0xb0d]=(loadaddr>>8)+0xb;
        initaddr=loadaddr+0xb00;
        playaddr=loadaddr+0xa65;
        psidh[P_TIMING  ]=1; // CIA timing
        strcpy(ids,"Electrosound");
        return 1;
    }
    return 0;
}
/***** PollyTracker **********************************************************/
int Chk_PollyTracker(void)
{
    if(fsiz<0x400) return 0;
    if((loadaddr>=0x0800) &&
       (loadaddr<=0x080d) &&
       (*(unsigned int*)(p-loadaddr+2+0x819)==0x8D02A6AD) &&
       (*(unsigned int*)(p-loadaddr+2+0x81d)==0x38A9080C) &&
       (*(unsigned int*)(p-loadaddr+2+0x89f)==0x4a4a4a4a))
    {
        psidh[P_MARKER  ]='R';
        initaddr=0x80d;
        playaddr=0;
        psidh[P_FREEPAGE]=4;
        psidh[P_FREEPMAX]=4;
        k=0x80e - loadaddr+2;
        memmove(p+k,aPatchPolly1,sizeof(aPatchPolly1));
        k=0x873 - loadaddr+2;
        memmove(p+k,aPatchPolly2,sizeof(aPatchPolly2));
        k=0x8b7 - loadaddr+2;
        p[k++]=0xa9;
        k=0x8c8 - loadaddr+2;
        memset(p+k,0xea,3);
        k=0x9a4 - loadaddr+2;
        memset(p+k,0xea,3);
        strcpy(ids,"PollyTracker");
        return 1;
    }
    return 0;
}
/***** Polyanna **************************************************************/
int Chk_Polyanna(void)
{
    if(fsiz<0x1000) return 0;
    if((loadaddr>=0x0800) &&
       (loadaddr<=0x080d) &&
       (*(unsigned int*)(p-loadaddr+2+0x80d)==0xFFA2D878) &&
       (*(unsigned int*)(p-loadaddr+2+0x81b)==0xD02005AD) &&
       (*(unsigned int*)(p-loadaddr+2+0x100c)==0xA9FFFB8D))
    {
        psidh[P_MARKER  ]='R';
        initaddr=0x154d;
        playaddr=0;
        k=initaddr - loadaddr+2;
        memmove(p+k,aPatchPolyAn,sizeof(aPatchPolyAn));
        strcpy(ids,"Polyanna");
        return 1;
    }
    return 0;
}
/***** Master Composer *******************************************************/
int Chk_MasterComp(void)
{
    if(fsiz<0x400) return 0;
    j = -1;
    for(k=0;k<fsiz-0x300;k++)
    {
        if((*(unsigned int*)(p+k+0x02)==0x29D404AD) &&
           (*(unsigned int*)(p+k+0x06)==0xD4048DFE) &&
           (*(unsigned int*)(p+k+0x12)==0x29D412AD) &&
           ((*(unsigned int*)(p+k+0x16)&0xff00ffff)==0xD4008DFE) &&
           (*(unsigned short int*)(p+k+0x9c)==(unsigned short int)(k+loadaddr))) /* JMP to k */
        {
            j=k;
            break;
        }
    }
    if(j != -1)
    {
        p+=j;
        fsiz-=j;
        loadaddr+=j;
        initaddr=(loadaddr - 0x0d);
        playaddr=(loadaddr - 0x06);
        extrabytes[0]=initaddr&0xff;
        extrabytes[1]=initaddr>>8;
        memmove(extrabytes+2,aPatchMastCm,sizeof(aPatchMastCm));
        extrabytes[5]=(loadaddr - 0x05)&0xff;
        extrabytes[6]=(loadaddr - 0x05)>>8;
        p[0]=0x60;
        p[1]=0x00;
        extra=13;
        j=0;
        psidh[P_TIMING  ]=1; // CIA timing
        // fix by Professor Chaos, should write to $d412 not $d404, it will
        // silence end of tunes correctly
        k=j+0x18;
        if (p[k]==0x04)
           p[k]=0x12;
        k=j+0x1a;
        memset(p+k,0x60,3);
        k=j+0x36;
        memset(p+k,0x60,3);
        k=j+0x85;
        p[k]=0xea;
        k=j+0x90;
        memset(p+k,0xea,0x0b);
        p[k++]=0xa9;
        p[k++]=0x00;
        p[k++]=0x8d;
        p[k++]=(loadaddr - 0x05)&0xff;
        p[k++]=(loadaddr - 0x05)>>8;
        k=j+0x24c;
        memset(p+k,0x60,3);
        k=j+0x25a;
        p[k++]=0xea;
        p[k++]=0x4c;
        p[k++]=(loadaddr+0x26b)&0xff;
        p[k++]=(loadaddr+0x26b)>>8;
        k=j+0x265;
        p[k]=0xea;
        k=j+0x289;
        memset(p+k,0xea,0x0c);
        strcpy(ids,"Master Composer");
        return 1;
    }
    return 0;
}
/***** Ubik's music **********************************************************/
int Chk_Ubik(void)
{
    if(fsiz<0x400) return 0;
    j = -1;
    for(k=0x68;k<fsiz-0x300;k++)
    {
        if((p[k]==0xad) &&
           (*(unsigned int*)(p+k+0x03)==0x22D00330) &&
           (*(unsigned int*)(p+k+0x07)==0x7F291860) &&
           (*(unsigned int*)(p+k+0x30)==0xA8306918))
        {
            j=k;
            break;
        }
    }
    if(j != -1)
    {
        k=j-0x66;
        initaddr=k+loadaddr-2;
        playaddr=initaddr+3;
        memset(p+k,0,0x66);
        memmove(p+k,aPatchUbiksM,sizeof(aPatchUbiksM));
        k++;
        p[k++]=(playaddr+3)&0xff;
        p[k++]=(playaddr+3)>>8;
        k++;
        p[k++]=(playaddr+22)&0xff;
        p[k++]=(playaddr+22)>>8;
        k+=4;
        p[k++]=p[j+1];
        p[k++]=p[j+2];
        k+=21;
        p[k++]=(j+loadaddr-2)&0xff;
        p[k++]=(j+loadaddr-2)>>8;
        psidh[P_SUBTUNES]=9; // there can be subtunes
        strcpy(ids,"Ubik's Music");
        return 1;
    }
    return 0;
}
/***** AMP 1.x variable around $13xx *****************************************/
int Chk_AMP1(void)
{
    if(fsiz<0x600) return 0;
    j = -1;
    for(k=0x300;k<0x400;k++)
    {
        if((*(unsigned int*)(p+k)==0x0BB015E0) &&
           (p[k+0x4]==0xad) &&
           (p[k+0x7]==0x3d) &&
           (p[k+0xa]==0xf0) )
        {
            playaddr=k;
            j=8;
            while(j>0&&p[playaddr]!=0x60)
            {
                playaddr--;
                j--;
            }
            if(j>0)
            {
                j = -1;
                for(;k<0x400;k++)
                {
                    if((p[k  ]==0x60) &&
                       (p[k+1]==0xa9))
                    {
                        j=k+1;
                        break;
                    }
                }
                if(j>0)
                {
                    playaddr++;
                    playaddr+=loadaddr-2;
                    initaddr=j;
                    initaddr+=loadaddr-2;
                }
                else
                {
                    playaddr=initaddr+3;
                }
            }
            break;
        }
    }
    if(j>0)
    {
        strcpy(ids,"AMP 1.x");
        return 1;
    }
    return 0;
}
/***** Boogaloo **************************************************************/
int Chk_Boogaloo(void)
{
    if(fsiz<0x200) return 0;
    if((p[0x2]==0x4c) &&
       (p[0xd]==0xd4) &&
       (*(unsigned int*)(p+0x05)==0x9DAA0029))
    {
        initaddr=loadaddr+3;
        playaddr=loadaddr+0;
        strcpy(ids,"Boogaloo");
        return 1;
    }
    return 0;
}
/***** Bjerregaard: TAX+$1000, variable play around $10xx ********************/
int Chk_Bjerregaard1(void)
{
    if(fsiz<0x200) return 0;
    j = -1;
    if(p[2]==0x4c)
    {
        for(k=0x00;k<0x100;k++)
        {
            if((p[k    ]==0xad) &&
               (*(unsigned int*)(p+k+3)==0xCE600110) &&
               (p[k+0x9]==0x10) )
            {
                j=k;
                break;
            }
        }
    }
    if(j>0)
    {
        initaddr=loadaddr-1;
        extrabytes[0]=initaddr&0xff;
        extra=1;
        p[0]=initaddr>>8;
        p[1]=0xaa;
        j=k+loadaddr-2;
        if(p[5]==0x4c)
        {
            k=p[6]|p[7]<<8;
            if(j!=k)
            {
                playaddr=j;
            }
        }
        else
        {
            playaddr=j;
        }
        strcpy(ids,"Bjerregaard");strcat(ids," v1");
        return 1;
    }
    return 0;
}
/***** Bjerregaard v2: $109b/10a1 ********************************************/
int Chk_Bjerregaard2(void)
{
    if(fsiz<0x200) return 0;
    j = -1;
    for(k=0;k<=0xff;k++)
    {
        if((p[k+0x00]==0x4c) &&
           (p[k+0x03]==0x4c) &&
           (p[k+0x06]==0x4c) &&
           (p[k+0x1b]==0xa9) &&
           (*(unsigned int*)(p+k+0x1d)==0xA26001D0) &&
           (*(unsigned int*)(p+k+0x21)==0xA5DDC602) )
        {
            j=k;
            break;
        }
    }
    if (j>0)
    {
        initaddr=loadaddr+k-2;
        playaddr=initaddr+6;
        strcpy(ids,"Bjerregaard");strcat(ids," v2");
        return 1;
    }
    return 0;
}
/***** Reflextracker *********************************************************/
int Chk_ReflexTrk(void)
{
    if((fsiz+loadaddr > 0xc500) && (fsiz+loadaddr < 0xd000))
    {
        if((*(unsigned int*)(p+0xc000-loadaddr+2)==0x4CC02C4C) &&
           (*(unsigned short int*)(p+0xc004-loadaddr+2)==0xC016) &&
           (*(unsigned int*)(p+0xc00a-loadaddr+2)==0xC02C2001) )
        {
            initaddr=0xc006;
            playaddr=0;
            psidh[P_MARKER  ]='R';
            strcpy(ids,"ReflexTracker");
            return 1;
        }
    }
    return 0;
}
/***** FAME ******************************************************************/
int Chk_FAME(void)
{
    if(fsiz<0x300) return 0;
    j = -1;
    for(k=0;k<0x80;k++)
    {
        if((p[k+0x00]==0xaa) &&
           (p[k+0x01]==0xbd) &&
           (p[k+0x04]==0x8d) &&
           (p[k+0x35]==0x4c) &&
           (p[k+0x38]==0xa2) &&
           (*(unsigned int*)(p+k+0x07)==0x50850A8A) &&
           (*(unsigned int*)(p+k+0x0b)==0x5065180A))
        {
            j=k;
            initaddr=j+loadaddr-2;
            playaddr=j+loadaddr-2+0x38;
            break;
        }
    }
    if (j>0)
    {
        strcpy(ids,"FAME");strcat(ids," v1");
        return 1;
    }
    j = -1;
    for(k=0;k<0xff;k++)
    {
        if(*(unsigned int*)(p+k+0x00)==0xA959A2A8)
        {
            j=k;
            for(;k<0x200;k++)
            {
                if((*(unsigned int*)(p+k+0x00)== 0x7D1898C8) &&
                   (p[k+0x0e]==0x4c) &&
                   (p[k+0x11]==0x4c) &&
                   (p[k+0x14]==0xa2))
                {
                    initaddr=j+loadaddr-2;
                    playaddr=k+loadaddr-2+0x14;
                    break;
                }
            }
            if(k==0x200)
            {
                j = -1;
            }
            break;
        }
    }
    if (j>0)
    {
        strcpy(ids,"FAME");strcat(ids," v2");
        return 1;
    }
    if((p[0x2]==0x4c) &&
       (p[0x9]==0x8d) &&
       (*(unsigned int*)(p+0x05)==0x00A959A2))
    {
        initaddr=loadaddr+3;
        playaddr=loadaddr+0;
        strcpy(ids,"FAME");strcat(ids," v3");
        return 1;
    }
    return 0;
}
/***** 20CC ******************************************************************/
int Chk_20CC(void)
{
    if(fsiz<0x300) return 0;
    j = -1;
    for(k=0;k<=0xff;k++)
    {
        if((p[k+0x00]==0xa9) &&
           (p[k+0x02]==0x30) &&
           (p[k+0x04]==0xf0) &&
           (p[k+0x0a]==0xb9) &&
           (p[k+0x10]==0xb9) &&
           (p[k+0x0d]==0x8d) &&
           (p[k+0x13]==0x8d) &&
           (*(unsigned int*)(p+k+0x06)==0xa80a0a0a) )
        {
            j=k;
            break;
        }
        if((p[k+0x00]==0xa0) &&
           (p[k+0x02]==0x30) &&
           (p[k+0x04]==0xf0) &&
           (p[k+0x06]==0x88) &&
           (p[k+0x07]==0x98) &&
           (p[k+0x0c]==0xb9) &&
           (*(unsigned int*)(p+k+0x08)==0xa80a0a0a) )
        {
            j=k;
            break;
        }
        if((p[k+0x00]==0xa0) &&
           (p[k+0x02]==0x30) &&
           (p[k+0x04]==0xf0) &&
           (p[k+0x06]==0xA2) &&
           (p[k+0x07]==0x17) &&
           (p[k+0x15]==0x8E) &&
           (p[k+0x22]==0xb9))
        {
            j=k;
            break;
        }
    }
    if (j>0)
    {
        extra=6;
        initaddr=loadaddr-extra;
        playaddr=j+loadaddr-2;
        k=0;
        extrabytes[k++]=initaddr&0xff;
        extrabytes[k++]=initaddr>>8;
        extrabytes[k++]=0xa9;
        extrabytes[k++]=0x01;
        extrabytes[k++]=0x8d;
        extrabytes[k++]=(playaddr+1)&0xff;
        p[0]=(playaddr+1)>>8;
        p[1]=0x60;
        strcpy(ids,"20CC");strcat(ids," v1");
        return 1;
    }
    if((p[2]==0xa4)&&
       (p[8]==0x4c)&&
       (*(unsigned int*)(p+0x04)==0x03F00930) &&
       (*(unsigned int*)(p+0x0c)==0xA260D418) )
    {
        extra=5;
        initaddr=loadaddr-extra;
        playaddr=loadaddr;
        k=0;
        extrabytes[k++]=initaddr&0xff;
        extrabytes[k++]=initaddr>>8;
        extrabytes[k++]=0xa9;
        extrabytes[k++]=0x01;
        extrabytes[k++]=0x85;
        p[0]=p[3];
        p[1]=0x60;
        strcpy(ids,"20CC");strcat(ids," v2");
        return 1;
    }
    return 0;
}
/***** Cybertracker/EXE ******************************************************/
int Chk_CTExe(void)
{
    if((loadaddr == 0x800)&&(fsiz>0x4000)&&
       (*(unsigned int*)(p+0x3ee1)==0x9AFFA278) &&
       (*(unsigned int*)(p+0x4001)==0x4C4A7D4C) &&
       (*(unsigned int*)(p+0x40dc)==0x4a4a4a4a) )
    {
        initaddr=0x53A2;
        playaddr=0x53E2;
        if(p[0x4be7]==0x20) /* rasterbar */
           p[0x4be7]=0x2c;
        strcpy(ids,"Cybertracker/EXE");
        return 1;
    }
    return 0;
}
/***** System6581 LDA#2+JSR$1000/LDA#1+JSR$1000 ******************************/
int Chk_System6581(void)
{
    if(fsiz<0x200) return 0;
    j = -1;
    if(((*(unsigned int*)(p+0x02)&0x0fffffff)==0x092CF0AA)&&
        (*(unsigned int*)(p+0x17)==0xD4009DAA) &&
        (*(unsigned int*)(p+0x22)==0x8E01A2F5) )
    {
        j = 7;
        strcpy(ids,"System6581");strcat(ids," v1");
    }
    else if((*(unsigned int*)(p+0x02)==0xC930F0A8) &&
            (*(unsigned int*)(p+0x06)==0x4C35D001) &&
           ((*(unsigned int*)(p+0x43)&0xff1fffff)==0xD4009DAA) &&
            (*(unsigned int*)(p+0x4d)==0x3898F5D0) )
    {
        j = 7;
        strcpy(ids,"System6581");strcat(ids," v2");
    }
    if(j>0)
    {
        extra=j;
        initaddr=loadaddr-extra;
        playaddr=loadaddr-2;
        k=0;
        extrabytes[k++]=initaddr&0xff;
        extrabytes[k++]=initaddr>>8;
        extrabytes[k++]=0x18;
        extrabytes[k++]=0x69;
        extrabytes[k++]=0x02;
        extrabytes[k++]=0xd0;
        extrabytes[k++]=0x02;
        p[0]=0xa9;
        p[1]=0x01;
        return 1;
    }
    return 0;
}
/***** Matt Gray: LDA #01 STA $1000/$1002 ************************************/
int Chk_MattGray(void)
{
    if(fsiz<0x200) return 0;
    if((p[0x04]==0xa2)&&
       (p[0x05]==0x00)&&
       (p[0x06]==0x20)&&
       (p[0x13]==0x60)&&
       (p[0x14]==0xad)&&
       (p[0x15]==(loadaddr&0xff))&&
       (p[0x16]==(loadaddr>>8)  )&&
       (p[0x1d]==0xc9)&&
       (p[0x1e]==0xab) )
    {
        extra=6;
        initaddr=loadaddr-extra;
        playaddr=loadaddr+2;
        k=0;
        extrabytes[k++]=initaddr&0xff;
        extrabytes[k++]=initaddr>>8;
        extrabytes[k++]=0xa9;
        extrabytes[k++]=0x01;
        extrabytes[k++]=0x8d;
        extrabytes[k++]=(loadaddr&0xff);
        p[0]=(loadaddr>>8)  ;
        p[1]=0x60;
        strcpy(ids,"Matt Gray");
        return 1;
    }
    return 0;
}
/***** Power Music: LDA #subtune+1 STA $1000/$1001 ***************************/
int Chk_PowerMus(void)
{
    if(fsiz<0x200) return 0;
    if((p[0x03]==0xad)&&
       (p[0x04]==0x00)&&
       (p[0x05]==(loadaddr>>8))&&
       (*(unsigned int*)(p+0x06)==0x01103AF0) &&
       (*(unsigned int*)(p+0x0a)==0x01E93860) )
    {
        extra=7;
        initaddr=loadaddr-extra;
        playaddr=loadaddr+1;
        k=0;
        extrabytes[k++]=initaddr&0xff;
        extrabytes[k++]=initaddr>>8;
        extrabytes[k++]=0x18;
        extrabytes[k++]=0x69;
        extrabytes[k++]=0x01;
        extrabytes[k++]=0x8d;
        extrabytes[k++]=(loadaddr&0xff);
        p[0]=(loadaddr>>8)  ;
        p[1]=0x60;
        strcpy(ids,"Power Music");
        return 1;
    }
    return 0;
}
/***** GRG tiny2:variable entry points ***************************************/
int Chk_GRGTiny2(void)
{
    if(fsiz<0x100) return 0;
    j = 0;
    for(k=0;k<fsiz-0x20;k++)
    {
        if((p[k  ]==0xa2) &&
           (p[k+1]==0x0e) &&
           (p[k+2]==0x86) )
        {
            playaddr=k+loadaddr-2;
            j|=1;
        }
        if((p[k  ]==0xa9) &&
           (p[k+1]==0x60) )
        {
            if(((p[k+2]==0x8d)&&(p[k+5]==0xa2))||
               ((p[k+2]==0x85)&&(p[k+4]==0xa2)))
            {
                initaddr=k+loadaddr-2;
                // there could be a AD 86 02 D0 some bytes before this
                // it's a self mod code to play the tune in ntsc
                for(i=k-4;i>k-0x20;i--)
                {
                    if((*(unsigned int*)(p+i)&0xffffffac)==0xD002A6Ac)
                    {
                        initaddr=i+loadaddr-2;
                        break;
                    }
                }
                j|=2;
            }
        }
        if(j==3)
        {
            break;
        }
    }
    if(j==3)
    {
        strcpy(ids,"GRG Tiny2");
        return 1;
    }
    initaddr=loadaddr;
    playaddr=initaddr+3;
    return 0;
}
/***** GRG tiny4:variable entry points ***************************************/
int Chk_GRGTiny4(void)
{
    if(fsiz<0x100) return 0;
    j = 0;
    for(k=0;k<fsiz-0x20;k++)
    {
        // variant 1
        if((p[k  ]==0xa2) &&
           (p[k+1]==0x0e) &&
           (p[k+2]==0xb5) &&
           (p[k+4]==0xf0) &&
           (p[k+6]==0xd6) &&
           (p[k+8]==0xd0) )
        {
            playaddr=k+loadaddr-2;
            j|=1;
        }
        // variant 2
        if((p[k  ]==0xa2) &&
           (p[k+1]==0x0e) &&
           (p[k+2]==0xb4) &&
           (p[k+4]==0xb5) &&
           (p[k+6]==0x10) &&
           (p[k+8]==0xa5) )
        {
            playaddr=k+loadaddr-2;
            j|=1;
        }
        if((p[k  ]==0xa9) &&
           (p[k+1]==0x00) &&
           (p[k+2]==0xa2) &&
           ((p[k+3]==0x14)||(p[k+3]==0x16)) &&
           (p[k+6]==0xd4) )
        {
            initaddr=k+loadaddr-2;
            j|=2;

        }
        if(j==3)
        {
            break;
        }
    }
    if(j==3)
    {
        strcpy(ids,"GRG Tiny4");
        return 1;
    }
    initaddr=loadaddr;
    playaddr=initaddr+3;
    return 0;
}
/***** Yip Megasound: $1000/$102e or $10xx/$10xx+$2e *************************/
int Chk_Yip(void)
{
    if(fsiz<0x200) return 0;
    j = 0;
    for(k=0;k<0x4f;k++)
    {
        if((p[k     ]==0xa9) &&
           (p[k+0x01]==0x01) &&
           (p[k+0x02]==0x8d) &&
           (p[k+0x28]==0xa9) &&
           (p[k+0x2e]==0xad) &&
           (p[k+0x31]==0xd0) &&
           (p[k+0x32]==0x20) &&
           (p[k+0x33]==0x60)
          )
        {
            j=1;
            initaddr=k+loadaddr-2;
            playaddr=initaddr+0x2e;
            break;
        }
    }
    if(j==1)
    {
        strcpy(ids,"Yip Megasound");
    }
    return j;
}
/***** TFX 1.0 : $1106/$1100 *************************************************/
int Chk_TFX1(void)
{
    if(fsiz<0x200) return 0;
    if((p[0x102]==0x4c)&&
       (p[0x105]==0x4c)&&
       (p[0x10e]==0xa8)&&
       (p[0x10f]==0xb9)&&
       (*(unsigned int*)(p+0x108)==0x8d0a0a0a)
      )
    {
        initaddr=loadaddr+0x106;
        playaddr=loadaddr+0x100;
        strcpy(ids,"TFX 1.0");
        return 1;
    }
    return 0;
}
/***** Griff v1: TAY+$1048/$10e0 *********************************************/
int Chk_Griff1(void)
{
    if(fsiz<0x200) return 0;
    if((*(unsigned int*)(p+0x48 +0x02)==0x00A900A2) &&
       (*(unsigned int*)(p+0x4E +0x02)==0x033C9DD4) &&
       (*(unsigned int*)(p+0x92 +0x02)==0x6003808D) &&
       (*(unsigned int*)(p+0xe0 +0x02)==0xF0039CAD)
      )
    {
        k=2;
        p[k++]=0x4c;
        p[k++]=(loadaddr+0x47)&0xff;
        p[k++]=(loadaddr+0x47)>>8;
        p[k++]=0x4c;
        p[k++]=(loadaddr+0xe0)&0xff;
        p[k++]=(loadaddr+0xe0)>>8;
        p[0x47+2]=0xa8;
        initaddr=loadaddr;
        playaddr=loadaddr+3;
        strcpy(ids,"Griff");
        return 1;
    }
    return 0;
}
/***** Griff v2/LightVoices: TAY+$1000/$1003 *********************************/
int Chk_Griff2(void)
{
    if(fsiz<0x200) return 0;
    if((p[2]==0x4c)&&
       (*(unsigned int*)(p+0x00+0x05)==0xF003A8AD) &&
       (*(unsigned int*)(p+0x04+0x05)==0x50AD6001) &&
       (*(unsigned int*)(p+0x08+0x05)==0xD4188D03) &&
       (*(unsigned int*)(p+0x0C+0x05)==0x8D0351AD)
      )
    {
        initaddr=loadaddr-1;
        extrabytes[0]=initaddr&0xff;
        extra=1;
        p[0]=initaddr>>8;
        p[1]=0xa8;
        strcpy(ids,"Griff");
        strcat(ids,"/LightVoices");
        return 1;
    }
    return 0;
}
/***** Ariston TAX+INX+STX $1000/$1001 ***************************************/
int Chk_Ariston(void)
{
    if(fsiz<0x200) return 0;
    j=-1;

    for(k=0;k<5;k++)
    {
        if((p[k+0x03]==0xad)&&
           ((p[k+0x04]|(p[k+0x05]<<8))==(loadaddr+k))&&
           (p[k+0x06]==0xd0)&&
           (p[k+0x07]==0x09)&&
           (p[k+0x08]==0x8d)&&
           (p[k+0x0b]==0x20)&&
           (p[k+0x0e]==0x4c)&&
           (p[k+0x0d]==p[k+0x10])
          )
        {
            j=k;
            break;
        }
        if((p[k+0x03]==0xad)&&
           ((p[k+0x04]|(p[k+0x05]<<8))==(loadaddr+k))&&
           (p[k+0x06]==0xc9)&&
           (p[k+0x07]==0xff)&&
           (p[k+0x08]==0xf0)&&
           (p[k+0x09]==0x3c)&&
           (p[k+0x17]==0x20)&&
           (p[k+0x1a]==0x4c)&&
           (p[k+0x1c]==p[k+0x19])
          )
        {
            j=k;
            break;
        }
    }
    if(j>=0)
    {
        playaddr=loadaddr+k+1;
        initaddr=loadaddr-6;
        extrabytes[0]=initaddr&0xff;
        extrabytes[1]=initaddr>>8;
        extrabytes[2]=0xaa;
        extrabytes[3]=0xe8;
        extrabytes[4]=0x8e;
        extrabytes[5]=p[k+0x04];
        extra=6;
        p[0]=p[k+0x05];
        p[1]=0x60;
        strcpy(ids,"Ariston");
        return 1;
    }
    return 0;
}
/***** Winterberg $102a/$105a ************************************************/
int Chk_Winterberg(void)
{
    if(fsiz<0x200) return 0;
    j=-1;
    for (i=2;i<0x30;i++)
    {
        if((*(unsigned int*)(p+i)==0x9D8A00A2) &&
           (*(unsigned short int*)(p+0x04+i)==(loadaddr&0xff00)) &&
           (*(unsigned int*)(p+0x06+i)==0xD02AE0E8) &&
           (*(unsigned int*)(p+0x37+i)==0x4C03F000)
          )
        {
            j=i;
            break;
        }
    }
    if(j>=0)
    {
        initaddr=loadaddr+i-2;
        playaddr=initaddr+0x30;
        psidh[P_TIMING  ]=1; // CIA timing
        j=i+0x10;
        memset(p+j,0xea,10);
        p[j+ 0]=0xa9;
        p[j+ 1]=0x25;
        p[j+ 2]=0x8d;
        p[j+ 3]=0x04;
        p[j+ 4]=0xdc;
        p[0x143+i]=0x60;
        strcpy(ids,"Winterberg");
        return 1;
    }
    return 0;
}
/***** Henrik Jensen $100f/$1015 *********************************************/
int Chk_Jensen(void)
{
    if(fsiz<0x800) return 0;
    k=-1;
    for (i=0;i<0x10;i++)
    {
        if((p[0x0e +i]==0x4c)&&
           (p[0x11 +i]==0x4c)&&
           (p[0x14 +i]==0x4c)&&
           (p[0x17 +i]==0xce)&&
           (p[0x1a +i]==0xce)&&
           (p[0x20 +i]==0xa9)&&
           (*(unsigned int*)(p+0x5b +i)==0x0AD00F30) )
        {
            k=i;
            break;
        }
    }
    if(k>=0)
    {
        initaddr=loadaddr+0x0f+k;
        playaddr=loadaddr+0x15+k;
        strcpy(ids,"Henrik Jensen");
        return 1;
    }
    return 0;
}
/***** MegaVision lda #$80+$1000/$103e ***************************************/
int Chk_MegaVision(void)
{
    if(fsiz<0xb00) return 0;
    if((p[0x0f]==0xad)&&
       (p[0x10]==0x2d)&&
       (*(unsigned int*)(p+0x05c)==0xD40099A8) &&
       (*(unsigned int*)(p+0x060)==0xD018C0C8) &&
       (*(unsigned int*)(p+0x1e0)==0x60E93809) )
    {
        k=2;
        p[k++]=0xa9;
        p[k++]=0x80;
        p[k++]=0x8d;
        p[k++]=0x28;
        p[k++]=loadaddr>>8;
        memset(p+7,0xea,8);
        p[0x26]=0x60;
        p[0x36]=0x60;
        p[0x904]=0x60; // 4c31ea
        psidh[P_TIMING  ]=1; // CIA timing, not always needed
        initaddr=loadaddr;
        playaddr=loadaddr+0x3e;
        strcpy(ids,"MegaVision");
        return 1;
    }
    return 0;
}
/***** SkylineTech/Danne: $1003/$1000 (usually $a83/$a80) ********************/
int Chk_SkylineTech_Danne(void)
{
    if(fsiz<0x600) return 0;
    i=loadaddr+0x5d;
    i<<=8;
    i|=0xad00004c;
    if(
       (*(unsigned int*)(p+0x02)==i) &&
       (*(unsigned int*)(p+0x08)==0xA903418D) &&
       (*(unsigned int*)(p+0x4a)==0xD4009DAA) &&
       (*(unsigned int*)(p+0x90)==0x0341AD03)
      )
    {
        initaddr=loadaddr+3;
        playaddr=loadaddr+0;
        strcpy(ids,"SkylineTech/Danne");
        i=fixsklstack(p+2,fsiz-2);
        if(i==0x100)
        {
            strcat(ids," (fixed)");
        }
        return 1;
    }
    return 0;
}
/***** Deflemask v2/v12 ******************************************************/
int Chk_Deflemask(void)
{
    // loadaddr can be $1000 or $1006 if already cut by sidclean
    if(fsiz<0x200) return 0;
    // v2 until v11
    for (i=2;i<=8;i+=6)
    {
        if((*(unsigned int*)(p+0x00c-6+i)==0x02D013E6) &&
           (*(unsigned int*)(p+0x010-6+i)==0x84AD14E6) &&
           (*(unsigned int*)(p+0x049-6+i)==0xCAD40099) )
        {
            initaddr=loadaddr&0xff00;
            playaddr=initaddr+3;
            j=((initaddr>>8)&0xff)+1;
            if(i==8)
            {
                i=2;
                p[i++]=0x4c;
                p[i++]=0x0f;
                p[i++]=j;
                p[i++]=0x4c;
                p[i++]=0x17;
                p[i++]=j;
            }
            else
            {
                extra=6;
                extrabytes[0]=initaddr&0xff;
                extrabytes[1]=initaddr>>8;
                extrabytes[2]=0x4c;
                extrabytes[3]=0x0f;
                extrabytes[4]=j;
                extrabytes[5]=0x4c;
                p[0]         =0x17;
                p[1]         =j;

            }
            strcpy(ids,"Deflemask v2");
            return 1;
        }
    }
    // v12
    for (i=2;i<=8;i+=6)
    {
        if(((*(unsigned int*)(p+0x006-6+i)&0x00ffffff)==0x00B518A2) &&
           (*(unsigned int*)(p+0x00a-6+i)==0xCAD4009D) &&
           (*(unsigned int*)(p+0x05d-6+i)==0xA500FF60) )
        {
            initaddr=loadaddr&0xff00;
            playaddr=initaddr+6;
            j=((initaddr>>8)&0xff)+1;
            if(i==8)
            {
                i=2;
                p[i++]=0x4c;
                p[i++]=0x03;
                p[i++]=j;
                p[i++]=0x4c;
                p[i++]=playaddr&0xff;
                p[i++]=playaddr>>8;
            }
            else
            {
                extra=6;
                extrabytes[0]=initaddr&0xff;
                extrabytes[1]=initaddr>>8;
                extrabytes[2]=0x4c;
                extrabytes[3]=0x03;
                extrabytes[4]=j;
                extrabytes[5]=0x4c;
                p[0]         =playaddr&0xff;
                p[1]         =playaddr>>8;

            }
            strcpy(ids,"Deflemask v12");
            return 1;
        }
    }
    // v12 large mem
    if(((*(unsigned int*)(p+0x002)&0x00ffffff)==0x00B518A2) &&
       (*(unsigned int*)(p+0x06)==0xCAD4009D) &&
       (*(unsigned int*)(p+0x60)==0xA500FF60) )
    {
        initaddr=loadaddr+0x106;
        playaddr=loadaddr;
        strcpy(ids,"Deflemask v12");
        strcat(ids,"/bank-switched");
        return 1;
    }
    return 0;
}

/***** SidFactory: $1000/$1006-1009 ******************************************/
int Chk_SidFactory(void)
{
    if(fsiz<0x200) return 0;
    if(p[0x2]==0x4c)
    {
        for (k=6;k<=9;k+=3)
        {
            if((p[k+2+0x00]==0x2c)&&
               (p[k+2+0x03]==0x30)&&
               (p[k+2+0x05]==0x70)&&
               (p[k+2+0x07]==0xa9)&&
               (p[k+2+0x08]==0x00)&&
               (p[k+2+0x09]==0xa2)&&
               (p[k+2+0x0b]==0xca))
            {
                initaddr=loadaddr;
                playaddr=loadaddr+k;
                strcpy(ids,"SidFactory");
                return 1;
            }
        }
    }
    return 0;
}
/***** Mssiah: $5c7c -> patch $5c20 ******************************************/
/* notes
unp64 -R$950 name.prg
there is a PSID at $5c00, needs patching

ID:
5c7c: A9 80 8D 5A 71 20 F3 5E 20 1C 5F 20 9B 5E A2 F6

patch by Inge/HVSC
5C20: 78 A9 35 85 01 20 1C 5F 20 F3 5E A9 00 8D 0E DC 8D 0F DC 8D 19 D0 8D 1A D0 A9 7F 8D 0D DC A9 81 8D 0D DC A9 94 8D FE FF A9 5F 8D FF FF A9 A4 8D FA FF A9 5F 8D FB FF A9 F6 2C 5A 71 30 02 A9 AC 8D 04 DC A9 07 8D 05 DC A9 11 8D 0E DC A9 1B 8D 11 D0 58 20 95 5E 60
5F26: 60
more patches by iAN CooG/HVSC
5F89: A2 (it is already but some of the sids in HVSC have RTS here)
617F: EA EA EA (99 67 06  STA $0667,Y  -> nop x3)
6185: EA EA EA (99 74 06  STA $0674,Y  -> nop x3)

change the $1200-12ff buffer to $5b00-5bff to gain more freepages
(offset from 5c7c)
028A: 12 5B
0979: 12 5B
097F: 12 5B
0FAF: 12 5B
0FB5: 12 5B
10E6: 12 5B
10EF: 12 5B

stereo sid flag:
at $7186 (offset from 5c7c=0x150a)
    if 0=single sid
    if 1=2nd sid @ $DE00
    if 2=2nd sid @ $DF00
    if 3=2nd sid @ $D500

save as RSID from 5C20
*/
int Chk_Mssiah(void)
{
    if(fsiz<0x5000) return 0;
    if(loadaddr>0x5c7c) return 0;
    j=0x5c7c-loadaddr+2;
    if((*(unsigned int*)(p+j+0x0)==0x5A8D80A9) &&
       (*(unsigned int*)(p+j+0x4)==0x5EF32071) &&
       (*(unsigned int*)(p+j+0x8)==0x205F1C20) &&
       (*(unsigned int*)(p+j+0xc)==0xF6A25E9B) )
    {
        psidh[P_MARKER  ]='R';
        initaddr=0x5c20;
        playaddr=0;

        p+=j;
        fsiz-=j;
        loadaddr+=j;
        p[0x02aa]=0x60;
        p[0x030d]=0xA2;
        // screen writes
        j=0x0503;
        p[j++]=0xea;
        p[j++]=0xea;
        p[j++]=0xea;
        j=0x0509;
        p[j++]=0xea;
        p[j++]=0xea;
        p[j++]=0xea;

        // buffer $1200->$5b00
        p[0x028A]=0x5B;
        p[0x0979]=0x5B;
        p[0x097F]=0x5B;
        p[0x0FAF]=0x5B;
        p[0x0FB5]=0x5B;
        p[0x10E6]=0x5B;
        p[0x10EF]=0x5B;
        psidh[P_FREEPAGE]=0x04;
        psidh[P_FREEPMAX]=0x57;

        // 2sid?
        j=0x150a;
        if( p[j] > 0 )
        {
            p[j] = 3; // force d500, fuck de00/df00
            psidh[P_SIDVER  ]=3;
            psidh[P_STEREOAD]=0x50;
            k=(psidh[P_SIDMODEL]&0x30)<<2;
            psidh[P_SIDMODEL]|=k;
        }

        extrabytes[0]=initaddr&0xff;
        extrabytes[1]=initaddr>>8;
        memmove(extrabytes+2,aPatchMssiah,sizeof(aPatchMssiah));
        extra=2+sizeof(aPatchMssiah);

        strcpy(ids,"Mssiah");
        return 1;
    }
    return 0;
}
/***** GoatTracker+MultiSpeed: $0ff6/$1003 ***********************************/
int Chk_GoatMultispeed(void)
{
    double speed=0;
    char pspeed[32]={0};
    if(fsiz<0x500) return 0;
    k=2;
    if((p[k+0x00]==0xa2)&&
       (p[k+0x0D]==0x4C)&&
       (*(unsigned int*)(p+k+0x02)==0xA2DC048E)&&
       (*(unsigned int*)(p+k+0x07)==0x4CDC058E)
      )
    {
        psidh[P_TIMING  ]=1; // CIA timing
        playaddr=initaddr+0xd;
        speed=(1.0*0x4cc8) / (p[k+1]|(p[k+6]<<8));
        sprintf(pspeed,"GoatTracker+MultiSpeed: %2.1fx",speed);
        strcpy(ids,pspeed);
        return 1;
    }
    return 0;
}
/***** FlexSid $1000/$1010 (normal) $1000/$100a (bare) ***********************/
int Chk_FlexSid(void)
{
    if(fsiz<0x100) return 0;
    j = 0;
    for(k=0;k<fsiz-0x20;k++)
    {
        if((*(unsigned int*)(p+k+0x00)==0xC19500AB)&&
           (*(unsigned int*)(p+k+0x0C)==0x60D4188E)&&
           (*(unsigned int*)(p+k+0x10)==0xFF860EA2))
        {
            j=1;
            initaddr=k+loadaddr-2;
            playaddr=k+loadaddr-2+0x10;
            strcpy(ids,"FlexSid");
            break;
        }
        if((*(unsigned int*)(p+k+0x00)==0x00A93FA2)&&
           (*(unsigned int*)(p+k+0x06)==0x60FB10CA)&&
           (*(unsigned int*)(p+k+0x0a)==0xFF860EA2))
        {
            j=2;
            initaddr=k+loadaddr-2;
            playaddr=k+loadaddr-2+0x0a;
            strcpy(ids,"FlexSid-Bare");
            break;
        }
    }
    if(j!=0)
    {
        return 1;
    }
    return 0;
}
/***** StarBars **************************************************************/
int Chk_StarBars(void)
{
    if(fsiz<0x1000) return 0;
    if((loadaddr>=0x0800) &&
       (loadaddr<=0x080d) )
    {
        if((*(unsigned int*)(p-loadaddr+2+0x80d)==0x0009BB4C) &&
           (*(unsigned int*)(p-loadaddr+2+0x89c)==0x4E494541) &&
           (*(unsigned int*)(p-loadaddr+2+0x1000)==0x8D1504AD))
        {
            j=*(unsigned char*)(p-loadaddr+2+0x9be);
            if((j==0x42) || (j==0x49))
            {
                psidh[P_MARKER  ]='R';
                psidh[P_SIDMODEL]=0x34; // fixed PAL & Any model
                strcpy(ids,"StarBars ");
                initaddr=0x09bb;
                playaddr=0;
                // common patches between 1.1 and 1.2
                k=0x08B1 - loadaddr+2;
                memset(p+k,0, 0x99);
                k=0x09c0 - loadaddr+2;
                memset(p+k,0xea, 0x6b);
                k=0x0a5b - loadaddr+2;
                p[k++]=0x60;
                memset(p+k,0, 0x05a4);
                k=0x1300 - loadaddr+2;
                memset(p+k,00, 0x100);
                // now deal with different versions offsets
                if(j==0x42)
                {
                    k=0x10b1 - loadaddr+2;
                    memset(p+k,0x60, 0x1e);
                    k=0x11e1 - loadaddr+2;
                    memset(p+k,0xea, 0x29);
                    k=0x122b - loadaddr+2;
                    memset(p+k,0x60, 0x17);
                    k=0x1271 - loadaddr+2;
                    memset(p+k,0x60, 0x12);
                    k=0x129c - loadaddr+2;
                    memset(p+k,0x60, 0x20);

                    strcat(ids,"v1.1");
                }
                else
                {
                    k=0x10a1 - loadaddr+2;
                    memset(p+k,0x60, 0x1e);
                    k=0x11e8 - loadaddr+2;
                    memset(p+k,0xea, 0x29);
                    k=0x1232 - loadaddr+2;
                    memset(p+k,0x60, 0x17);
                    k=0x1278 - loadaddr+2;
                    memset(p+k,0x60, 0x12);
                    k=0x12a3 - loadaddr+2;
                    memset(p+k,0x60, 0x20);

                    strcat(ids,"v1.2");
                }
                return 1;
            }
        }
        if((*(unsigned int*)(p-loadaddr+2+0x80d)==0x0920D878) &&
           (*(unsigned int*)(p-loadaddr+2+0xb0b)==0x4E494541) &&
           (*(unsigned int*)(p-loadaddr+2+0x930)==0x8D1504AD))
        {
            j=*(unsigned char*)(p-loadaddr+2+0x0810);
            if(j==0x09)
            {
                psidh[P_MARKER  ]='R';
                psidh[P_SIDMODEL]=0x34; // fixed PAL & Any model
                strcpy(ids,"StarBars ");
                initaddr=0x080d;
                playaddr=0;

                k=0x0812 - loadaddr+2;
                memset(p+k,0xea, 0x90);
                k=0x08d8 - loadaddr+2;
                p[k++]=0x60;
                memset(p+k,0, 0x057);
                k=0x09d1 - loadaddr+2;
                memset(p+k,0x60, 0x1e);
                k=0x0b20 - loadaddr+2;
                memset(p+k,0, 0x4e0);
                k=0x10a5 - loadaddr+2;
                memset(p+k,0xea, 0x29);
                k=0x10f2 - loadaddr+2;
                memset(p+k,0x60, 0x17);
                k=0x1138 - loadaddr+2;
                memset(p+k,0x60, 0x98);
                k=0x11e8 - loadaddr+2;
                memset(p+k,0x60, 0x21);
                k=0x120a - loadaddr+2;
                memset(p+k,0, 0x1f6);
                k=0x141c - loadaddr+2;
                memset(p+k,0, 0xe4);

                strcat(ids,"v1.3");
                strcat(ids,"beta");
                return 1;
            }
        }
        if((*(unsigned int*)(p-loadaddr+2+0x80d)==0x00A9D878) &&
           (*(unsigned int*)(p-loadaddr+2+0xb1d)==0x4E494541) &&
           (*(unsigned int*)(p-loadaddr+2+0x92f)==0x8D1504AD))
        {
            j=*(unsigned char*)(p-loadaddr+2+0x0819);
            if(j==0x04)
            {
                psidh[P_MARKER  ]='R';
                psidh[P_SIDMODEL]=0x34; // fixed PAL & Any model
                strcpy(ids,"StarBars ");
                initaddr=0x080d;
                playaddr=0;
                k=0x0818 - loadaddr+2;
                memset(p+k,0xea, 0x7b);
                k=0x08e6 - loadaddr+2;
                memset(p+k,0x60, 0x49);
                k=0x09E3 - loadaddr+2;
                memset(p+k,0x60, 0x1e);
                k=0x0b32 - loadaddr+2;
                memset(p+k,0, 0x4ce);
                k=0x10b4 - loadaddr+2;
                memset(p+k,0xea, 0x1c);
                k=0x10d7 - loadaddr+2;
                memset(p+k,0x60, 0x3e);
                k=0x111c - loadaddr+2;
                memset(p+k,0x60, 0x10);
                k=0x113f - loadaddr+2;
                memset(p+k,0x60, 0x92);
                k=0x1204 - loadaddr+2;
                memset(p+k,0x60, 0x20);
                k=0x128d - loadaddr+2;
                memset(p+k,0, 0x173);
                k=0x141c - loadaddr+2;
                memset(p+k,0, 0xe4);

                strcat(ids,"v1.3");
                return 1;
            }
        }
        if((*(unsigned int*)(p-loadaddr+2+0x80d)==0x00A9D878) &&
           (*(unsigned int*)(p-loadaddr+2+0xb21)==0x4E494541) &&
           (*(unsigned int*)(p-loadaddr+2+0x929)==0x8D1504AD))
        {
            j=*(unsigned char*)(p-loadaddr+2+0x0819);
            if(j==0x04)
            {
                psidh[P_MARKER  ]='R';
                psidh[P_SIDMODEL]=0x34; // fixed PAL & Any model
                strcpy(ids,"StarBars ");
                initaddr=0x080d;
                playaddr=0;
                k=0x0818 - loadaddr+2;
                memset(p+k,0xea, 0x75);

                k=0x08e0 - loadaddr+2;
                memset(p+k,0x60, 0x48);

                k=0x09E7 - loadaddr+2;
                memset(p+k,0x60, 0x1e);

                k=0x0b36 - loadaddr+2;
                memset(p+k,0, 0x4ca);

                k=0x10b4 - loadaddr+2;
                memset(p+k,0xea, 0x1c);
                k=0x10d7 - loadaddr+2;
                memset(p+k,0x60, 0x3e);
                k=0x111c - loadaddr+2;
                memset(p+k,0x60, 0x10);
                k=0x113f - loadaddr+2;
                memset(p+k,0x60, 0x92);
                k=0x1204 - loadaddr+2;
                memset(p+k,0x60, 0x20);
                k=0x128d - loadaddr+2;
                memset(p+k,0, 0x173);
                k=0x141c - loadaddr+2;
                memset(p+k,0, 0xe4);

                strcat(ids,"v1.4");
                strcat(ids,"beta");
                return 1;
            }
        }
        if((*(unsigned int*)(p-loadaddr+2+0x80d)==0xAA00A978) &&
           (*(unsigned int*)(p-loadaddr+2+0xb20)==0x4E494541) &&
           (*(unsigned int*)(p-loadaddr+2+0x901)==0x8D1504AD))
        {
            j=*(unsigned char*)(p-loadaddr+2+0x0818);
            if(j==0x04)
            {
                psidh[P_MARKER  ]='R';
                psidh[P_SIDMODEL]=0x34; // fixed PAL & Any model
                strcpy(ids,"StarBars ");
                initaddr=0x080d;
                playaddr=0;
                k=0x0817 - loadaddr+2;
                memset(p+k,0xea, 0x4e);

                k=0x08b8 - loadaddr+2;
                memset(p+k,0x60, 0x48);

                k=0x09D6 - loadaddr+2;
                memset(p+k,0x60, 0x1e);

                k=0x0b35 - loadaddr+2;
                memset(p+k,0, 0x4cb);

                k=0x10b4 - loadaddr+2;
                memset(p+k,0xea, 0x1c);
                k=0x10d7 - loadaddr+2;
                memset(p+k,0x60, 0x3e);
                k=0x111c - loadaddr+2;
                memset(p+k,0x60, 0x10);
                k=0x113f - loadaddr+2;
                memset(p+k,0x60, 0x92);
                k=0x1204 - loadaddr+2;
                memset(p+k,0x60, 0x20);
                k=0x128d - loadaddr+2;
                memset(p+k,0, 0x173);
                k=0x141c - loadaddr+2;
                memset(p+k,0, 0x95);

                strcat(ids,"v1.4");
                return 1;
            }
        }
    }
    return 0;
}
/***** Quantum SoundTracker **************************************************/
int Chk_QuantumSndTrk(void)
{   // if there are enough bytes to patch, ok, else don't identify
    // else it will write outside the read memory.
    if(fsiz<(0xdd8f+0x3c+2-loadaddr)) return 0;
    if((loadaddr>=0x0800) &&
       (loadaddr<=0x080d) )
    {
        if((*(unsigned int*)(p-loadaddr+2+0x80f)==0x8534A90D) &&
           (*(unsigned int*)(p-loadaddr+2+0x89b)==0x4A4A4A8A) &&
           (*(unsigned int*)(p-loadaddr+2+0x9AF)==0xEDF0DD0D))
        {
            j=*(unsigned char*)(p-loadaddr+2+0x80e);
            if((j==0x6a) || (j==0x6c))
            {
                psidh[P_MARKER  ]='R';
                //psidh[P_SIDMODEL]=0x14; // fixed PAL & 6581
                psidh[P_FREEPAGE]=4;
                psidh[P_FREEPMAX]=4;
                strcpy(ids,"Quantum SoundTracker 1.0");

                // common patches
                k=0x0821 - loadaddr+2;
                memset(p+k,0xea, 0x03);

                k=0x082c - loadaddr+2;
                memset(p+k,0x78, 0x0c);

                k=0x08e7 - loadaddr+2;
                memset(p+k,0x60, 0x56);

                k=0x0fc0 - loadaddr+2;
                memset(p+k,0x60, 0x3f);

                k=0xdd6d - loadaddr+2;
                memset(p+k,0xea, 0x03);

                k=0xdd73 - loadaddr+2;
                memset(p+k,0xea, 0x03);

                k=0xdd8f - loadaddr+2;
                memset(p+k,0x60, 0x3c);

                // the "no limit" demo track has 2 byte offset
                // compared to the actual generated binaries in 1.0
                if (j==0x6c)
                {
                	strcat(ids,"/demo");
                    k=0x0a3e - loadaddr+2;
                    memset(p+k,0x60, 0x2e6);

                    k=0x0d8a - loadaddr+2;
                    memset(p+k,0x60, 0xb9);
                }
                else
                {
                    k=0x0a3e - loadaddr+2;
                    memset(p+k,0x60, 0x2e4);

                    k=0x0d88 - loadaddr+2;
                    memset(p+k,0x60, 0xb9);
                }
                initaddr=0x080d;
                playaddr=0;
                return 1;
            }
        }
    }
    return 0;
}
/***** Whittaker *************************************************************/
int Chk_Whittaker(void)
{
    if(fsiz<0x800) return 0;
    i=0;
    for(k=0;k<0x800;k++)
    {
        if(*(unsigned int*)(p+k)==0x8D00A9AA)
        {
            i=k;
            break;
        }
    }
    if (i>0)
    {
        for(j=i;j<0x800;j++)
        {
            if((*(unsigned int*)(p+j )==0xA548F8A5) &&
               (p[j+0x06]==0xCE) &&
               (p[j+0x09]==0xD0) &&
               (p[j+0x10]==0xD0) &&
               (p[j+0x12]==0x20)
              )
            {
                initaddr=loadaddr+k-2;
                playaddr=loadaddr+j-2;
                strcpy(ids,"Whittaker");
                strcat(ids," v1");
                return 1;
            }
            if((*(unsigned int*)(p+j )==0xA548F8A5) &&
               (p[j+0x06]==0x20) &&
               (p[j+0x0f]==0x60) &&
               (p[j+0x15]==0xCE) &&
               (p[j+0x18]==0xD0) &&
               (p[j+0x1C]==0x20)
              )
            {
                initaddr=loadaddr+k-2;
                playaddr=loadaddr+j-2;
                strcpy(ids,"Whittaker");
                strcat(ids," v2");
                return 1;
            }
        }
    }
    return 0;
}
/*****************************************************************************/

typedef int(*Scnptr)(void);

Scnptr ScanFunc[]=
{Chk_FC
,Chk_FCAlt
,Chk_MusAss
,Chk_MusMix
,Chk_GMC
,Chk_Bappalander
,Chk_TrkPl3
,Chk_Groovy
,Chk_Parsec
,Chk_Sosperec
,Chk_SoedeSoft
,Chk_Prosonix1
,Chk_4JMPS
,Chk_Heathcliff
,Chk_3JMPs1
,Chk_ArneAFL
,Chk_ArneSndMk
,Chk_Digitalizer
,Chk_Soundmon
,Chk_AMP2
,Chk_FC3x
,Chk_MoN_JTS
,Chk_3JMPs2
,Chk_JOv2
,Chk_2JMPs
,Chk_LaxityV2
,Chk_HubbardV5
,Chk_HubbardV4
,Chk_HubbardV3
,Chk_HubbardV2
,Chk_HubbardV1
,Chk_MikeLSD
,Chk_Comptech
,Chk_SoundMaker
,Chk_Electrosound
,Chk_PollyTracker
,Chk_MasterComp
,Chk_Ubik
,Chk_AMP1
,Chk_Boogaloo
,Chk_Bjerregaard1
,Chk_Bjerregaard2
,Chk_ReflexTrk
,Chk_FAME
,Chk_20CC
,Chk_CTExe
,Chk_System6581
,Chk_MattGray
,Chk_PowerMus
,Chk_GRGTiny2
,Chk_GRGTiny4
,Chk_Yip
,Chk_TFX1
,Chk_Griff1
,Chk_Griff2
,Chk_Ariston
,Chk_Winterberg
,Chk_Jensen
,Chk_MegaVision
,Chk_SkylineTech_Danne
,Chk_Deflemask
,Chk_Polyanna
,Chk_SidFactory
,Chk_Mssiah
,Chk_GoatMultispeed
,Chk_FlexSid
,Chk_StarBars
,Chk_Whittaker
,Chk_QuantumSndTrk
};

/*****************************************************************************/
int Scanners(void)
{
    int x,y,z=0;
    y=sizeof(ScanFunc)/sizeof(*ScanFunc);
    for (x=0;x<y;x++)
    {
        z=(ScanFunc[x])();
        if( z )
            break;
    }
    return z;
}

/*****************************************************************************/
int main(int argc, char *argv[])
{
    char newfile[MAX_PATH],*z,*q, tempstr[40]={0};
    unsigned char *realp;
    FILE *h,*hout;

    if(argc<2)
    {
        printf(
        "PRG2SID "VERSION" (/) iAN CooG/HVSC\n"
        "Usage: p2s <filename.prg> [load_addr] [6/8] [P/N]"
        " [Title] [Author] [Release] [Songs] [Startsong]\n"
        "A filename.sid will be created.\n"
        "Optional parameters\n"
        "load_addr: start ripping from this address ($ or 0x for hex)\n"
        "6 for 6581 (default) or 8 for 8580\n"
        "P for PAL  (default) or N for NTSC\n"
        "Title, Author, Release must be 32 chars or less\n"
        "Songs and startsong between 1 (default) and 255\n"
        );
        return 1;
    }
    strcpy(newfile,argv[1]);
    z=strrchr(newfile,'\\');
    if(z)
    {
        q=strrchr(z,'.');
    }
    else
    {
        q=strrchr(newfile,'.');
    }
    if(q)
        *q=0;
    strcat(newfile,".sid");
    h=fopen(argv[1],"rb");
    if(h==NULL)
    {
        printf("error opening %s\n",argv[1]);
        return 2;
    }
    fseek(h,0,SEEK_END);
    fsiz=ftell(h);
    fseek(h,0,SEEK_SET);
    realp=calloc(fsiz,1);
    p=realp;
    if(realp==NULL)
    {
        printf("alloc error??\n");
        fclose(h);
        return 3;
    }
    fread(p,fsiz,1,h);
    fclose(h);
    if(((p[P_MARKER+0]==psidh[P_MARKER+0])||(p[P_MARKER+0]=='R')) &&
        (p[P_MARKER+1]==psidh[P_MARKER+1]) &&
        (p[P_MARKER+2]==psidh[P_MARKER+2]) &&
        (p[P_MARKER+3]==psidh[P_MARKER+3]))
    {
        printf("%s is already a .SID\n",argv[1]);
        free(realp);
        return 2;
    }
    hout=fopen(newfile,"wb");
    if(hout==NULL)
    {
        free(realp);
        printf("error creating %s\n",newfile);
        return 4;
    }
    loadaddr=p[0]|p[1]<<8;
    if( (argc>2) && (strlen(argv[2])>2) )
    {
        j=0;
        if(argv[2][0]=='$')
            j=strtol(argv[2]+1,&q,16);
        else if( (argv[2][0]=='0') && ((argv[2][1]&0xdf)=='X') )
            j=strtol(argv[2]+2,&q,16);
        else
            j=strtol(argv[2],&q,10);
        if((j>loadaddr) && (j<(loadaddr+fsiz-2)))
        {
            k=j-loadaddr;
            p+=k;
            fsiz-=k;
            loadaddr=j;
            p[0]=j&0xff;
            p[1]=j>>8;
        }
    }
    if( (argc>3) && (strlen(argv[3])>0) )
    {
        if(argv[3][0]=='8')
        {
            j=psidh[P_SIDMODEL]&0x0f;
            j|=0x20;
            psidh[P_SIDMODEL]=j;
        }
    }
    if( (argc>4) && (strlen(argv[4])>0) )
    {
        if((argv[4][0]&0x5f)=='N')
        {
            j=psidh[P_SIDMODEL]&0xf0;
            j|=0x8;
            psidh[P_SIDMODEL]=j;
        }
    }
    if( (argc>5) && (strlen(argv[5])>0) ) /* idea by Wisdom/Crescent */
    {
        memset(tempstr,0,sizeof(tempstr));
        strncpy(tempstr,argv[5],32);
        printf("Title   : %s\n", tempstr);
        memcpy(psidh+P_NAME, tempstr, 32);
    }
    if( (argc>6) && (strlen(argv[6])>0) )
    {
        memset(tempstr,0,sizeof(tempstr));
        strncpy(tempstr,argv[6],32);
        printf("Author  : %s\n", tempstr);
        memcpy(psidh+P_AUTHOR, tempstr, 32);
    }
    if( (argc>7) && (strlen(argv[7])>0) )
    {
        memset(tempstr,0,sizeof(tempstr));
        strncpy(tempstr,argv[7],32);
        printf("Released: %s\n", tempstr);
        memcpy(psidh+P_RELEASED, tempstr, 32);
    }
    if( (argc>8) && (strlen(argv[8])>0) )
    {
        j=strtol(argv[8],&q,10);
        if((j>0) && (j<256))
        {
            psidh[P_SUBTUNES]=j&0xff;
            printf("Subtunes: %d\n", j);
        }
    }
    if( (argc>9) && (strlen(argv[9])>0) )
    {
        j=strtol(argv[9],&q,10);
        if((j>0) && (j<256))
        {
            psidh[P_STARTSNG]=j&0xff;
            printf("StartSng: %d\n", j);
        }
    }
    /* default for classic 1000/1003 */
    initaddr=loadaddr;
    playaddr=initaddr+3;
    /* briefly id some particular players */
    Scanners();
    printf("%s: ID=%s Init=$%04x Play=$%04x\n",newfile,ids,initaddr,playaddr);
    psidh[P_INITADDR+0]=initaddr>>8;
    psidh[P_INITADDR+1]=initaddr&0xff;
    psidh[P_PLAYADDR+0]=playaddr>>8;
    psidh[P_PLAYADDR+1]=playaddr&0xff;
    fwrite(psidh,sizeof(psidh),1,hout);
    if(extra)
    {
        fwrite(extrabytes,extra,1,hout);
        if(extra==1)
        {
            loadaddr=extrabytes[0]|p[0]<<8;
        }
        else
        {
            loadaddr=extrabytes[0]|extrabytes[1]<<8;
        }
    }

    j=fsiz+loadaddr+extra-2;
    if (j>0xffff)
    {
        fsiz-=(j-0x10000);
    }
    fwrite(p,fsiz,1,hout);
    fclose(hout);
    free(realp);
    return 0;
}
