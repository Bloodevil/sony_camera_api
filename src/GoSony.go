//# Common Header
//# 0--------1--------2--------+--------4----+----+----+----8
//# |0xFF    |payload | sequence number | Time stamp        |
//# |        |type    |                 |                   |
//# +-------------------------------------------------------+
//#
//# Payload Header
//# 0--------------------------4-------------------7--------8
//# | Start code               |  JPEG data size   | Padding|
//# +--------------------------4------5---------------------+
//# | Reserved                 | 0x00 | ..                  |
//# +-------------------------------------------------------+
//# | .. 115[B] Reserved                                    |
//# +-------------------------------------------------------+
//# | ...                                                   |
//# ------------------------------------------------------128
//#
//# Payload Data
//# in case payload type = 0x01
//# +-------------------------------------------------------+
//# | JPEG data size ...                                    |
//# +-------------------------------------------------------+
//# | ...                                                   |
//# +-------------------------------------------------------+
//# | Padding data size ...                                 |
//# ------------------------------JPEG data size + Padding data size

package GoSony

import (
	"io"
	"net/http"
	"net/url"
	"fmt"
)

type CommonHeader struct {
	offset          int8
	Payload_type    int8
	Sequence_number int16
	Timestamp       uint32
}

type PayloadHeader struct {
	Start_code     uint32
	JPEG_data_size uint16
	padding        int8
	reserved_1     uint32
	flag           int8
	//reserved_2  129-13
}

type SonyCameraFormat struct {
	Common  CommonHeader
	Payload PayloadHeader
	Data    []byte
}

func ParseSonyCameraData(rd io.Reader, dst *SonyCameraFormat) error {
	return error
}

func main() {
	n := "tcp"
	addr := "10.0.0.1:10000"
	l, err := net.Listen(n, addr)
	if err != nil {
		panic("AAAAH")
	}

	/* HTTP server */
	server := http.Server{
		Handler: http.HandlerFunc(handle),
	}
	server.Serve(l)
}
