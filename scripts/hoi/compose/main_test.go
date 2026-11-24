package main

import (
	"archive/tar"
	"bytes"
	"io"
	"testing"

	v1 "github.com/google/go-containerregistry/pkg/v1"
	"github.com/google/go-containerregistry/pkg/v1/empty"
	"github.com/google/go-containerregistry/pkg/v1/mutate"
	"github.com/google/go-containerregistry/pkg/v1/tarball"
)

func testImage(t *testing.T, path, contents string) v1.Image {
	t.Helper()
	var buf bytes.Buffer
	tw := tar.NewWriter(&buf)
	if err := tw.WriteHeader(&tar.Header{Name: path, Mode: 0644, Size: int64(len(contents))}); err != nil {
		t.Fatal(err)
	}
	if _, err := tw.Write([]byte(contents)); err != nil {
		t.Fatal(err)
	}
	if err := tw.Close(); err != nil {
		t.Fatal(err)
	}
	layer, err := tarball.LayerFromReader(bytes.NewReader(buf.Bytes()))
	if err != nil {
		t.Fatal(err)
	}
	img, err := mutate.AppendLayers(empty.Image, layer)
	if err != nil {
		t.Fatal(err)
	}
	return img
}

func TestComposePreservesBaseConfigAndAllFiles(t *testing.T) {
	base, err := mutate.Config(testImage(t, "workspace/grail/base", "base"), v1.Config{
		Env: []string{"BASE_ENV=present"}, WorkingDir: "/workspace/grail", Cmd: []string{"bash"},
		Volumes: map[string]struct{}{"/workspace/grail": {}, "/other": {}},
	})
	if err != nil {
		t.Fatal(err)
	}
	result, err := compose(base, []v1.Image{
		testImage(t, "opt/conda/envs/hoi/check", "hoi"),
		testImage(t, "opt/conda/envs/light/check", "light"),
	})
	if err != nil {
		t.Fatal(err)
	}
	config, err := result.ConfigFile()
	if err != nil {
		t.Fatal(err)
	}
	if config.Config.WorkingDir != "/workspace/grail" || len(config.Config.Env) != 1 || config.Config.Env[0] != "BASE_ENV=present" || len(config.Config.Cmd) != 1 || config.Config.Cmd[0] != "bash" {
		t.Fatalf("base configuration changed: %+v", config.Config)
	}
	if len(config.RootFS.DiffIDs) != 3 {
		t.Fatalf("expected three filesystem layers, got %d", len(config.RootFS.DiffIDs))
	}
	if _, ok := config.Config.Volumes["/workspace/grail"]; ok {
		t.Fatal("inherited GRAIL workspace must not be an anonymous volume")
	}
	if _, ok := config.Config.Volumes["/other"]; !ok {
		t.Fatal("unrelated base volumes must be preserved")
	}
	reader := mutate.Extract(result)
	defer reader.Close()
	tr := tar.NewReader(reader)
	found := make(map[string]string)
	for {
		h, err := tr.Next()
		if err == io.EOF {
			break
		}
		if err != nil {
			t.Fatal(err)
		}
		b, err := io.ReadAll(tr)
		if err != nil {
			t.Fatal(err)
		}
		found[h.Name] = string(b)
	}
	for path, want := range map[string]string{
		"workspace/grail/base": "base",
		"opt/conda/envs/hoi/check": "hoi",
		"opt/conda/envs/light/check": "light",
	} {
		if found[path] != want {
			t.Errorf("%s = %q, want %q", path, found[path], want)
		}
	}
}
