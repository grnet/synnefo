$TTL 14400
$origin %DOMAIN%.
@              IN      SOA     ns.%DOMAIN%. admin.%DOMAIN%. (
2012111903; the Serial Number
172800; the Refresh Rate
7200;  the Retry Time
604800; the Expiration Time
3600; the Minimum Time
)

@               IN      NS      ns.%DOMAIN%.
@               IN      A       %NS_NODE_IP%
ns              IN      A       %NS_NODE_IP%

localhost       IN      A       127.0.0.1
%DOMAIN%.       IN      MX      10 %DOMAIN%.

mail            IN      CNAME   %DOMAIN%.
www             IN      CNAME   %DOMAIN%.
