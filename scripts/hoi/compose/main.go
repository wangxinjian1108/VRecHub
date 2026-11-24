// Compose independently built OCI filesystem layers on a validated base.
// The images are combined in the registry, avoiding a full local extraction.
package main

import (
	"fmt"
	"os"
	"strings"

	"github.com/google/go-containerregistry/pkg/authn"
	"github.com/google/go-containerregistry/pkg/name"
	v1 "github.com/google/go-containerregistry/pkg/v1"
	"github.com/google/go-containerregistry/pkg/v1/mutate"
	"github.com/google/go-containerregistry/pkg/v1/remote"
)

// compose retains the base runtime configuration and appends component
// filesystem layers in order. Component images must contain only the intended
// absolute paths; they are exported separately from the verified runtimes.
func compose(base v1.Image, components []v1.Image) (v1.Image, error) {
	result := base
	for index, component := range components {
		layers, err := component.Layers()
		if err != nil {
			return nil, fmt.Errorf("component %d layers: %w", index, err)
		}
		result, err = mutate.AppendLayers(result, layers...)
		if err != nil {
			return nil, fmt.Errorf("append component %d: %w", index, err)
		}
	}
	return result, nil
}

func run() error {
	if len(os.Args) != 7 {
		return fmt.Errorf("usage: compose BASE@sha256:... HOI@sha256:... LIGHT@sha256:... INTERACT@sha256:... HAIC@sha256:... DESTINATION:tag")
	}
	refs := make([]name.Reference, 5)
	images := make([]v1.Image, 5)
	opts := []remote.Option{remote.WithAuthFromKeychain(authn.DefaultKeychain), remote.WithPlatform(v1.Platform{OS: "linux", Architecture: "amd64"})}
	for i, raw := range os.Args[1:6] {
		if !strings.Contains(raw, "@sha256:") {
			return fmt.Errorf("source image must be pinned by sha256 digest: %q", raw)
		}
		ref, err := name.ParseReference(raw, name.StrictValidation)
		if err != nil {
			return fmt.Errorf("invalid source reference: %w", err)
		}
		refs[i] = ref
		images[i], err = remote.Image(ref, opts...)
		if err != nil {
			return fmt.Errorf("read %s: %w", ref, err)
		}
	}
	dest, err := name.NewTag(os.Args[6], name.StrictValidation)
	if err != nil {
		return fmt.Errorf("invalid destination tag: %w", err)
	}
	for _, ref := range refs {
		if ref.Context().RegistryStr() != dest.Context().RegistryStr() {
			return fmt.Errorf("source and destination must use the same registry: %s", ref)
		}
	}
	result, err := compose(images[0], images[1:])
	if err != nil {
		return err
	}
	manifest, err := result.Manifest()
	if err != nil {
		return fmt.Errorf("assemble manifest: %w", err)
	}
	config, err := result.ConfigFile()
	if err != nil {
		return fmt.Errorf("assemble config: %w", err)
	}
	if len(manifest.Layers) != len(config.RootFS.DiffIDs) {
		return fmt.Errorf("layer / diff-id count mismatch: %d / %d", len(manifest.Layers), len(config.RootFS.DiffIDs))
	}
	fmt.Printf("Pushing %d layers to %s\n", len(manifest.Layers), dest)
	if err := remote.Write(dest, result, opts...); err != nil {
		return fmt.Errorf("push composed image: %w", err)
	}
	localDigest, err := result.Digest()
	if err != nil {
		return fmt.Errorf("calculate result digest: %w", err)
	}
	actual, err := remote.Image(dest, opts...)
	if err != nil {
		return fmt.Errorf("verify published image: %w", err)
	}
	actualDigest, err := actual.Digest()
	if err != nil || actualDigest != localDigest {
		return fmt.Errorf("published digest mismatch: got %s, want %s, error %v", actualDigest, localDigest, err)
	}
	fmt.Printf("Published candidate: %s@%s\n", dest.Context(), actualDigest)
	return nil
}

func main() {
	if err := run(); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}
