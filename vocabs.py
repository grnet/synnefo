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
                    "id" : 11,
                    "name" : "Ubuntu 10.10 server 64bit",
                    "updated" : "2010-10-10T12:00:00Z",
                    "created" : "2010-08-10T12:00:00Z",
                    "status" : "ACTIVE"
                },
                {
                    "id" : 4,
                    "name" : "FreeBSD 8.1 Release i386",
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
                    "id" : 1548,
                    "name" : "sample-server9",
                    "imageId" : 3,
                    "flavorId" : 1,
                    "hostId" : "9e107d9d372bb6826bd81d3542a419d6",
                    "status" : "ACTIVE",
                    "addresses" : {
                        "public" : [
                                "67.23.10.143"
                            ],
                        "private" : [
                                "10.176.42.21"
                            ]
                        },
                    "metadata" : {
                            "Server Label" : "DB 19"
                        }
                },

                {
                    "id" : 3678,
                    "name" : "sample-server19",
                    "imageId" : 3,
                    "flavorId" : 1,
                    "hostId" : "9e107d9d372bb6826bd81d3542a419d6",
                    "status" : "ACTIVE",
                    "addresses" : {
                        "public" : [
                                "67.23.10.118"
                            ],
                        "private" : [
                                "10.176.42.18"
                            ]
                        },
                    "metadata" : {
                            "Server Label" : "DB 5"
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
                },
                {
                "id" : 14354,
                "name" : "sample-server8",
                "imageId" : 3,
                "flavorId" : 1,
                "hostId" : "e4d909c290d0fb1ca068ffaddf22cbd0",
                "status" : "BUILD",
                "progress" : 20,
                "addresses" : {
                    "public" : [
                        "67.23.10.140",
                        "67.23.10.141"
                        ],
                    "private" : [
                        "10.176.42.24"
                        ]
                    },
                "metadata" : {
                        "Server Label" : "Web Head 8",
                        "Image Version" : "3.0"
                    }
                },
                {
                "id" : 1633,
                "name" : "sample-server33",
                "imageId" : 5,
                "flavorId" : 5,
                "hostId" : "e4d909c290d0fb1ca068ffaddf22cbd0",
                "status" : "BUILD",
                "progress" : 33,
                "addresses" : {
                    "public" : [
                        "67.23.10.133",
                        "67.23.10.133"
                        ],
                    "private" : [
                        "10.176.42.33"
                        ]
                    },
                "metadata" : {
                        "Server Label" : "My Web Server 33",
                        "Image Version" : "3.3"
                    }
                },

                {
                "id" : 16,
                "name" : "sample-server 66",
                "imageId" : 5,
                "flavorId" : 5,
                "hostId" : "e4d909c290d0fb1ca068ffaddf22cbd0",
                "status" : "BUILD",
                "progress" : 66,
                "addresses" : {
                    "public" : [
                        "67.23.10.166",
                        "67.23.10.166"
                        ],
                    "private" : [
                        "10.176.42.66"
                        ]
                    },
                "metadata" : {
                        "Server Label" : "My Web Server 66",
                        "Image Version" : "6.6"
                    }
                },

                {
                "id" : 1665,
                "name" : "sample-server28",
                "imageId" : 3,
                "flavorId" : 12,
                "hostId" : "e4d909c290d0fb1ca068ffaddf22cbd0",
                "status" : "BUILD",
                "progress" : 66,
                "addresses" : {
                    "public" : [
                        "67.23.10.150",
                        "67.23.10.129"
                        ],
                    "private" : [
                        "10.176.42.99"
                        ]
                    },
                "metadata" : {
                        "Server Label" : "My Web Server 18",
                        "Image Version" : "5.5"
                    }
                },

                {
                    "id" : 4758,
                    "name" : "my sample-server for mysql",
                    "imageId" : 6,
                    "flavorId" : 9,
                    "hostId" : "9e107d9d372bb6826bd81d3542a419d6",
                    "status" : "SUSPENDED",
                    "addresses" : {
                        },
                    "metadata" : {
                            "Server Label" : "Mysql DB production"
                        }
                },


                {
                    "id" : 1548,
                    "name" : "mongodb8",
                    "imageId" : 6,
                    "flavorId" :6,
                    "hostId" : "9e107d9d372bb6826bd81d3542a419d6",
                    "status" : "ACTIVE",
                    "addresses" : {
                        "public" : [
                                "67.23.11.55"
                            ],
                        "private" : [
                                "10.176.11.76"
                            ]
                        },
                    "metadata" : {
                            "Server Label" : "Mongodb production"
                        }
                },

                {
                    "id" : 3678,
                    "name" : "sample-server29",
                    "imageId" : 6,
                    "flavorId" : 6,
                    "hostId" : "9e107d9d372bb6826bd81d3542a419d6",
                    "status" : "ACTIVE",
                    "addresses" : {
                        "public" : [
                                "67.23.10.56"
                            ],
                        "private" : [
                                "10.176.42.58"
                            ]
                        },
                    "metadata" : {
                            "Server Label" : "Sample Server 29"
                        }
                },
                {
                    "id" : 156,
                    "name" : "sample-server15",
                    "imageId" : 3,
                    "flavorId" : 3,
                    "hostId" : "9e107d9d372bb6826bd81d3542a419d6",
                    "status" : "ACTIVE",
                    "addresses" : {
                        "public" : [
                                "67.23.10.96"
                            ],
                        "private" : [
                                "10.176.42.99"
                            ]
                        },
                    "metadata" : {
                            "Server Label" : "Sample Server 15"
                        }
                },

                {
                    "id" : 5620,
                    "name" : "sample-server20",
                    "imageId" : 3,
                    "flavorId" : 3,
                    "hostId" : "9e107d9d372bb6826bd81d3542a419d6",
                    "status" : "ACTIVE",
                    "addresses" : {
                        "public" : [
                                "67.23.10.20"
                            ],
                        "private" : [
                                "10.176.42.20"
                            ]
                        },
                    "metadata" : {
                            "Server Label" : "Sample Server 20"
                        }
                },

                {
                    "id" : 5629,
                    "name" : "sample-server29",
                    "imageId" : 6,
                    "flavorId" : 1,
                    "hostId" : "9e107d9d372bb6826bd81d3542a419d6",
                    "status" : "ACTIVE",
                    "addresses" : {
                        "public" : [
                                "67.23.10.29"
                            ],
                        "private" : [
                                "10.176.42.29"
                            ]
                        },
                    "metadata" : {
                            "Server Label" : "Sample Server 29"
                        }
                },


                {
                    "id" : 5673,
                    "name" : "sample-server77",
                    "imageId" : 6,
                    "flavorId" : 7,
                    "hostId" : "9e107d9d372bb6826bd81d3542a419d6",
                    "status" : "ACTIVE",
                    "addresses" : {
                        "public" : [
                                "67.23.10.77"
                            ],
                        "private" : [
                                "10.176.42.77"
                            ]
                        },
                    "metadata" : {
                            "Server Label" : "Sample Server 77"
                        }
                },


                {
                    "id" : 5480,
                    "name" : "sample-server4",
                    "imageId" : 3,
                    "flavorId" : 12,
                    "hostId" : "9e107d9d372bb6826bd81d3542a419d6",
                    "status" : "SUSPENDED",
                    "addresses" : {
                        },
                    "metadata" : {
                            "Server Label" : "DB 3"
                        }
                }
               ]

