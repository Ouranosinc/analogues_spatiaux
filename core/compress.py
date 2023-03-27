
def get_nbits(x):
    return len(bin(x)[2:])
def int_to_bin(x,xmax):
    ''' returns a binary string representing x, 
        e.g.: int_to_binary(12,16) =  [0,1,1,0,0]
    '''
    # number of bits required to represent xmax:
    nbits = get_nbits(xmax)
    # convert using bin, cut off prefix:
    binstr = bin(x)[2:]
    # cut off first bits if x > xmax:
    binstr = binstr[len(binstr)-min(nbits,len(binstr)):] 
    # prepend missing bits, if bin(x) < nbits:
    binstr = binstr.rjust(nbits,'0')
    return binstr

def bin_to_int(x):
    return int('0b'+x,2)

def bin_to_utf(binstr):
    '''Converts a binary string to a utf-8 encoded string.'''
    # convert list of bits [1, 0, 1...] to a utf-8 string
    #s = ''.join([str(x) for x in bitlist])
    bytelistb = [binstr[i:i+8].rjust(8,'0') for i in range(0, len(binstr), 8)] # bytelist of bits
    bytelistB = [int(b,2) for b in bytelistb]
    ustring = ''.join([chr(x) for x in bytelistB])
    return ustring

def utf_to_bin(ustring):
    bytelist = [ord(b) for b in ustring]
    return ''.join([bin(b)[2:].rjust(8,'0') for b in bytelist])

def pad_byte(L):
    # pads an integer array L so that it's full length is a multiple of 8 (i.e. it will easily become a byte list)
    return L + '0'*(8 - (len(L) % 8))

class Argument:
    type = None
    val = None
    max = None
    
    def __init__(self, **kwargs):
        
        if 'val' in kwargs:
            self.val = kwargs['val']
        if 'type' in kwargs:
            self.type = kwargs['type']
        if 'max' in kwargs:
            self.max = kwargs['max']
        
        if (not self.type) and self.val:
            self.type = type(self.val)
            
        if self.type == bool and not self.max:
            self.max = 1
            self.type = int
            self.val = int(self.val)
            
def simplify(args):
    binstr = ''
    for arg in args:
        if arg.type == int:
            binstr += int_to_bin(arg.val,arg.max)
    binstr = pad_byte(binstr)
    return bin_to_utf(binstr)

def unsimplify(utfstr,args):
    binstr = utf_to_bin(utfstr)
    
    for arg in args:
        if arg.type == int:
            nbits = get_nbits(arg.max)
            arg.val,binstr = bin_to_int(binstr[:nbits]),binstr[nbits:]
    return args, [arg.val for arg in args]

def simplify_ssp(ssp):
    return Argument(val=(ssp == 'ssp45'), type=bool)

def simplify_city(city,cities):
    for i,c in enumerate(cities.city):
        if c == city.city:
            return Argument(val = i, max = len(cities.city))
    

def simplify_climate(all_indices,climate_indices):
    return [Argument(val=(x in climate_indices)) for x in all_indices]

def simplify_item(item,options):
    for i,p in enumerate(options):
        if p == item:
            return Argument(val = i, max = len(options)) 

import inspect        
def simplify_args(best_analog_mode,analog_modes, # 2 bits
                   city, cities,            # 8 bits (65 cities)
                   climate_indices, all_indices,  # 20 bits all_indices = [x.name for k,x in dsim.data_vars.items()]
                   density_factor, max_density,   # 4 bits (up to 10)
                   tgt_period, periods,       # 4 bits (11 different ones)
                   ssp,ssp_list,              # 1 bit
                   num_realizations,max_real):# 4 bits (up to 12), total: 30+8+5 = 43 bits => 48/8 = 7 bytes
    args,_,_,values = inspect.getargvalues(inspect.currentframe()) # save a copy of the args to simplify. they will be unpacked later.
    
    ArgList = [simplify_item(ssp,ssp_list),
               simplify_item(best_analog_mode, analog_modes),
               simplify_item(tgt_period,periods),
               simplify_city(city,cities),
               *simplify_climate(all_indices,climate_indices),
               Argument(val=density_factor,max=max_density),
               Argument(val=num_realizations,max=max_real)]
    
    return simplify(ArgList), values

latmin = 20.
latmax = 85.
lonmin = -168.
lonmax = -48.
umax = 65535
scoremin = -50.
scoremax = 50.
zscale = 10.

def _to_short(site,zscore,score,lat,lon):
    # transform lat from 0 to 1:
    lat_to_norm = lambda lat : (lat - latmin) / (latmax - latmin)
    lon_to_norm = lambda lon : (lon - lonmin) / (lonmax - lonmin)
    zscore_to_norm = lambda zscore : zscore / zscale
    score_to_norm  = lambda score : (score - scoremin) / (scoremax - scoremin)

    # transform lat from 0 to 65535 (ushort)
    
    norm_to_short = lambda x: x * umax

    
    return (site, norm_to_short(zscore_to_norm(zscore)), norm_to_short(score_to_norm(score)), norm_to_short(lat_to_norm(lat)), norm_to_short(lon_to_norm(lon)))

def _to_float(site,zscore,score,lat,lon):
    # transform from ushortnorm to 0-1:
    short_to_norm = lambda x: x / umax

    # transform from unorm to lat,lon:
    norm_to_lat = lambda x: (x * (latmax - latmin)) + latmin
    norm_to_lon = lambda x: (x * (lonmax - lonmin)) + lonmin
    norm_to_score = lambda x: (x * (scoremax - scoremin)) + scoremin
    norm_to_zscore = lambda x: (x * zscale)
    return (site, norm_to_zscore(short_to_norm(zscore)), norm_to_score(short_to_norm(score)), norm_to_lat(short_to_norm(lat)), norm_to_lon(short_to_norm(lon)))