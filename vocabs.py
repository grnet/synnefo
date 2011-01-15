IMAGE_TAGS = {
                1: 'archlinux',
                2: 'centos',
                3: 'debian',
                4: 'freebsd',
                5: 'gentoo',
                6: 'netbsd',
                7: 'openbsd',
                8: 'redhat',
                9: 'slackware',
                10: 'suse',
                11: 'ubuntu',
                12: 'windows',
               }

MOCK_IMAGES = [
                {
                    "id" : 2,
                    "name" : "CentOS 5.2",
                    "updated" : "2010-10-10T12:00:00Z",
                    "created" : "2010-08-10T12:00:00Z",
                    "status" : "ACTIVE"
                },
                {
                    "id" : 3,
                    "name" : "Debian Lenny",
                    "updated" : "2010-10-10T12:00:00Z",
                    "created" : "2010-08-10T12:00:00Z",
                    "status" : "ACTIVE"
                },
                {
                    "id" : 11,
                    "name" : "Ubuntu 10.04 server 64bit",
                    "updated" : "2010-10-10T12:00:00Z",
                    "created" : "2010-08-10T12:00:00Z",
                    "status" : "ACTIVE"
                },
                {
                    "id" : 12,
                    "name" : "My Server Backup",
                    "serverId" : 12,
                    "updated" : "2010-10-10T12:00:00Z",
                    "created" : "2010-08-10T12:00:00Z",
                    "status" : "SAVING",
                    "progress" : 80
                },
              ]


MOCK_SERVERS = [
                {
                "id" : 1234,
                "name" : "sample-server",
                "imageId" : 11,
                "flavorId" : 1,
                "hostId" : "e4d909c290d0fb1ca068ffaddf22cbd0",
                "status" : "BUILD",
                "progress" : 60,
                "addresses" : {
                    "public" : [
                        "67.23.10.132",
                        "67.23.10.131"
                        ],
                    "private" : [
                        "10.176.42.16"
                        ]
                    },
                "metadata" : {
                        "Server Label" : "Web Head 1",
                        "Image Version" : "2.1"
                    }
                },
                {
                    "id" : 5678,
                    "name" : "sample-server2",
                    "imageId" : 6,
                    "flavorId" : 1,
                    "hostId" : "9e107d9d372bb6826bd81d3542a419d6",
                    "status" : "ACTIVE",
                    "addresses" : {
                        "public" : [
                                "67.23.10.133"
                            ],
                        "private" : [
                                "10.176.42.17"
                            ]
                        },
                    "metadata" : {
                            "Server Label" : "DB 1"
                        }
                },
                {
                    "id" : 890,
                    "name" : "sample-server3",
                    "imageId" : 12,
                    "flavorId" : 2,
                    "hostId" : "9e107d9d372bb6826bd81d3542a419d6",
                    "status" : "SUSPENDED",
                    "addresses" : {
                        },
                    "metadata" : {
                            "Server Label" : "DB 2"
                        }
                }
               ]

