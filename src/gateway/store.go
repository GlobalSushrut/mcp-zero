package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"sync"
)

// Store is a zero-dependency, file-backed key-value store.
// Data is organized as buckets (directories) containing JSON files (keys).
// This is NOT agent state (that lives in the Rust kernel's storage).
// This stores API metadata, request logs, and gateway configuration.
//
// Layout:
//   <root>/agents/agent_abc.json
//   <root>/meta/version.json
type Store struct {
	root string
	mu   sync.RWMutex
}

// NewStore opens or creates a file-backed store at the given path.
func NewStore(path string) (*Store, error) {
	// Create root and default buckets
	for _, bucket := range []string{"agents", "meta", "logs"} {
		dir := filepath.Join(path, bucket)
		if err := os.MkdirAll(dir, 0755); err != nil {
			return nil, fmt.Errorf("create bucket dir %s: %v", dir, err)
		}
	}
	return &Store{root: path}, nil
}

// Close is a no-op for the file store (satisfies interface).
func (s *Store) Close() error {
	return nil
}

// Put stores a key-value pair in the given bucket.
func (s *Store) Put(bucket, key string, value interface{}) error {
	data, err := json.Marshal(value)
	if err != nil {
		return fmt.Errorf("marshal value: %v", err)
	}

	s.mu.Lock()
	defer s.mu.Unlock()

	dir := filepath.Join(s.root, bucket)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return err
	}

	file := filepath.Join(dir, key+".json")
	return ioutil.WriteFile(file, data, 0644)
}

// Get retrieves a value from the given bucket.
func (s *Store) Get(bucket, key string) (json.RawMessage, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	file := filepath.Join(s.root, bucket, key+".json")
	data, err := ioutil.ReadFile(file)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, fmt.Errorf("key not found: %s", key)
		}
		return nil, err
	}
	return json.RawMessage(data), nil
}

// Delete removes a key from the given bucket.
func (s *Store) Delete(bucket, key string) error {
	s.mu.Lock()
	defer s.mu.Unlock()

	file := filepath.Join(s.root, bucket, key+".json")
	err := os.Remove(file)
	if err != nil && !os.IsNotExist(err) {
		return err
	}
	return nil
}

// List returns all keys in the given bucket.
func (s *Store) List(bucket string) ([]string, error) {
	s.mu.RLock()
	defer s.mu.RUnlock()

	dir := filepath.Join(s.root, bucket)
	entries, err := ioutil.ReadDir(dir)
	if err != nil {
		if os.IsNotExist(err) {
			return nil, nil
		}
		return nil, err
	}

	var keys []string
	for _, e := range entries {
		if e.IsDir() {
			continue
		}
		name := e.Name()
		if ext := filepath.Ext(name); ext == ".json" {
			keys = append(keys, name[:len(name)-len(ext)])
		}
	}
	return keys, nil
}
