.PHONY: deps firmware test hardware-check exports bundle
deps:
	bash tools/bootstrap.sh
firmware:
	$(MAKE) -C firmware
test:
	python3 tests/spectral_test.py
	cc -std=c11 -O1 -g -fsanitize=address,undefined -fno-omit-frame-pointer -Ifirmware tests/dsp_test.c firmware/dsp.c -lm -o build/dsp_sanitized
	ASAN_OPTIONS=detect_leaks=0 build/dsp_sanitized
hardware-check:
	/usr/bin/python3 tools/check_hardware.py
exports: hardware-check
	/usr/bin/python3 tools/export_manufacturing.py
bundle: test firmware exports
	python3 tools/package_release.py
