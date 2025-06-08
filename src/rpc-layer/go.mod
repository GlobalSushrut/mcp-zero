module github.com/mcp-zero/rpc-layer

go 1.13

require (
	github.com/prometheus/client_golang v1.7.1
	github.com/shirou/gopsutil v2.20.9+incompatible
	gopkg.in/yaml.v2 v2.3.0
)

// Force older versions of dependencies for Go 1.13 compatibility
replace (
	golang.org/x/net => golang.org/x/net v0.0.0-20190620200207-3b0461eec859
	golang.org/x/sys => golang.org/x/sys v0.0.0-20200615200032-f1bc736245b1
	golang.org/x/text => golang.org/x/text v0.3.2
)
