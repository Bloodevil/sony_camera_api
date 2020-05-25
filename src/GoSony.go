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

package main

import (
	"os"
	"bytes"
	"io"
	"io/ioutil"
	"fmt"
	"net"
	"net/http"
        "encoding/json"
	"mime/multipart"
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

const boundary = ""

//func ParseSonyCameraData(rd io.Reader, dst *SonyCameraFormat) error {
//	return error
//}

func handle(w http.ResponseWriter, req *http.Request) {
	partReader := multipart.NewReader(req.Body, boundary)
	buf := make([]byte, 256)
	for {
		part, err := partReader.NextPart()
		if err == io.EOF {
			break
		}
		var n int
		for {
			n, err = part.Read(buf)
			if err == io.EOF {
				break
			}
			fmt.Printf(string(buf[:n]))
		}
		fmt.Printf(string(buf[:n]))
	}
}

func main() {
    if len(os.Args) != 2 {
        fmt.Fprintf(os.Stderr, "Usage: %s host:port", os.Args[0])
        os.Exit(1)
    }
    service := os.Args[1]

    values := []byte(`{"method": "getAvailableApiList", "version": "1.0", "id": 1, "params": "[]"}`)
    jsonValue, _ := json.Marshal(values)

    resp, err := http.Post(service + "/sony/camera",
			"application/json",
                        jsonValue)
    if err != nil {
	checkError(err)	// handle error
    }
    defer resp.Body.Close()
    body, err := ioutil.ReadAll(resp.Body)
    fmt.Fprintf(os.Stderr, "%s", body)
    os.Exit(0)
}

func checkError(err error) {
    if err != nil {
        fmt.Fprintf(os.Stderr, "Fatal error: %s", err.Error())
        os.Exit(1)
    }
}

func readFully(conn net.Conn) ([]byte, error) {
    defer conn.Close()

    result := bytes.NewBuffer(nil)
    var buf [512]byte
    for {
        n, err := conn.Read(buf[0:])
        result.Write(buf[0:n])
        if err != nil {
            if err == io.EOF {
                break
            }
            return nil, err
        }
    }
    return result.Bytes(), nil
}
