var ASNIntValue, ASNLength, int2hex;
var encode64 = $.base64.encode;
function chars_from_hex(a){
    var c="";a=a.replace(/^(0x)?/g,"");
    a=a.replace(/[^A-Fa-f0-9]/g,"");
    a=a.split("");
    for(var b=0;b<a.length;b+=2)c+=String.fromCharCode(parseInt(a[b]+""+a[b+1],16));
        return c
};

RSAKey.prototype.privatePEM = function() {
  var encoded;
  encoded = '020100';
  encoded += ASNIntValue(this.n, true);
  encoded += ASNIntValue(this.e, false);
  encoded += ASNIntValue(this.d, false);
  encoded += ASNIntValue(this.p, true);
  encoded += ASNIntValue(this.q, true);
  encoded += ASNIntValue(this.dmp1, true);
  encoded += ASNIntValue(this.dmq1, false);
  encoded += ASNIntValue(this.coeff, false);
  encoded = '30' + ASNLength(encoded) + encoded;
    
  var lines = [];
  while(encoded.length > 48) {
    lines.push(encoded.slice(0, 48));
    encoded = encoded.slice(48);
  }

  lines.push(encoded);
  var content = "";
  for (var i = 0; i < lines.length; i++) {
    content = content + encode64(chars_from_hex(lines[i])) + "\n"; 
  }
  return "-----BEGIN RSA PRIVATE KEY-----\n" + content + "\n-----END RSA PRIVATE KEY-----";
};
RSAKey.prototype.publicPEM = function() {
  var encoded;
  encoded = ASNIntValue(this.n, true);
  encoded += ASNIntValue(this.e, false);
  encoded = '30' + ASNLength(encoded) + encoded;
  encoded = '03' + ASNLength(encoded, 1) + '00' + encoded;
  encoded = '300d06092a864886f70d0101010500' + encoded;
  encoded = '30' + ASNLength(encoded) + encoded;
  return "-----BEGIN PUBLIC KEY-----\n" + encode64(chars_from_hex(encoded)) + "\n-----END PUBLIC KEY-----";
};
RSAKey.prototype.parsePEM = function(pem) {
  pem = ASN1.decode(Base64.unarmor(pem)).sub;
  return this.setPrivateEx(pem[1].content(), pem[2].content(), pem[3].content(), pem[4].content(), pem[5].content(), pem[6].content(), pem[7].content(), pem[8].content());
};
ASNIntValue = function(integer, nullPrefixed) {
  integer = int2hex(integer);
  if (nullPrefixed) {
    integer = '00' + integer;
  }
  return '02' + ASNLength(integer) + integer;
};
ASNLength = function(content, extra) {
  var length;
  if (!(typeof extra !== "undefined" && extra !== null)) {
    extra = 0;
  }
  length = (content.length / 2) + extra;
  if (length > 127) {
    length = int2hex(length);
    return int2hex(0x80 + length.length / 2) + length;
  } else {
    return int2hex(length);
  }
};
int2hex = function(integer) {
  integer = integer.toString(16);
  if (integer.length % 2 !== 0) {
    integer = '0' + integer;
  }
  return integer;
};
