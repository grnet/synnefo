$TTL 14400
$origin vm.%DOMAIN%.
@              IN      SOA     ns.vm.%DOMAIN%. admin.vm.%DOMAIN%. (
2012111903; the Serial Number
172800; the Refresh Rate
7200;  the Retry Time
604800; the Expiration Time
3600; the Minimum Time
)

@               IN      NS      ns.vm.%DOMAIN%.
@               IN      A       %NS_NODE_IP%
ns              IN      A       %NS_NODE_IP%
