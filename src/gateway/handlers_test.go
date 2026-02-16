package main

import (
	"net/http"
	"net/http/httptest"
	"os"
	"strings"
	"testing"
)

func testStore(t *testing.T) (*Store, func()) {
	t.Helper()
	path := "/tmp/mcp_test_gateway_" + t.Name()
	os.RemoveAll(path)

	s, err := NewStore(path)
	if err != nil {
		t.Fatalf("NewStore: %v", err)
	}
	cleanup := func() {
		s.Close()
		os.RemoveAll(path)
	}
	return s, cleanup
}

func TestHealthEndpoint(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	if !strings.Contains(w.Body.String(), "ok") {
		t.Fatalf("expected 'ok' in body, got %s", w.Body.String())
	}
}

func TestListAgentsEmpty(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	req := httptest.NewRequest(http.MethodGet, "/api/v1/agents", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
	if !strings.Contains(w.Body.String(), `"count":0`) {
		t.Fatalf("expected count 0, got %s", w.Body.String())
	}
}

func TestStoreRoundtrip(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()

	err := store.Put("agents", "agent_1", map[string]string{"name": "test"})
	if err != nil {
		t.Fatalf("Put: %v", err)
	}

	data, err := store.Get("agents", "agent_1")
	if err != nil {
		t.Fatalf("Get: %v", err)
	}
	if !strings.Contains(string(data), "test") {
		t.Fatalf("expected 'test' in data, got %s", string(data))
	}

	keys, err := store.List("agents")
	if err != nil {
		t.Fatalf("List: %v", err)
	}
	if len(keys) != 1 || keys[0] != "agent_1" {
		t.Fatalf("expected [agent_1], got %v", keys)
	}

	err = store.Delete("agents", "agent_1")
	if err != nil {
		t.Fatalf("Delete: %v", err)
	}

	keys, err = store.List("agents")
	if err != nil {
		t.Fatalf("List after delete: %v", err)
	}
	if len(keys) != 0 {
		t.Fatalf("expected empty, got %v", keys)
	}
}

func TestGetMissingAgent(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()

	_, err := store.Get("agents", "nonexistent")
	if err == nil {
		t.Fatal("expected error for missing key")
	}
}

func TestMethodNotAllowed(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	req := httptest.NewRequest(http.MethodPut, "/api/v1/agents", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected 405, got %d", w.Code)
	}
}

func TestAgentByIDNotFound(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	req := httptest.NewRequest(http.MethodGet, "/api/v1/agents/nonexistent", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusNotFound {
		t.Fatalf("expected 404, got %d", w.Code)
	}
}

func TestExecuteMissingFields(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	req := httptest.NewRequest(http.MethodPost, "/api/v1/execute",
		strings.NewReader(`{"agent_id": ""}`))
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", w.Code)
	}
}

// --- Cognitive endpoint tests ---

func TestCogStateMethodNotAllowed(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	req := httptest.NewRequest(http.MethodPost, "/api/v1/cog/state", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected 405, got %d", w.Code)
	}
}

func TestCogCycleMethodNotAllowed(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	req := httptest.NewRequest(http.MethodGet, "/api/v1/cog/cycle", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected 405, got %d", w.Code)
	}
}

func TestCogIntentionMissingName(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	req := httptest.NewRequest(http.MethodPost, "/api/v1/cog/intention",
		strings.NewReader(`{"priority": 0.5}`))
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusBadRequest {
		t.Fatalf("expected 400, got %d", w.Code)
	}
}

func TestCogSearchMethodNotAllowed(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	req := httptest.NewRequest(http.MethodGet, "/api/v1/cog/search", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected 405, got %d", w.Code)
	}
}

func TestCogGroundMethodNotAllowed(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	req := httptest.NewRequest(http.MethodGet, "/api/v1/cog/ground", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected 405, got %d", w.Code)
	}
}

// --- Fabric endpoint tests ---

func TestFabricThinkMethodNotAllowed(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	req := httptest.NewRequest(http.MethodGet, "/api/v1/fabric/think", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected 405, got %d", w.Code)
	}
}

func TestFabricStatusMethodNotAllowed(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	req := httptest.NewRequest(http.MethodPost, "/api/v1/fabric/status", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected 405, got %d", w.Code)
	}
}

func TestFabricLearnMethodNotAllowed(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	req := httptest.NewRequest(http.MethodGet, "/api/v1/fabric/learn", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected 405, got %d", w.Code)
	}
}

func TestFabricTrainMethodNotAllowed(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	req := httptest.NewRequest(http.MethodGet, "/api/v1/fabric/train", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected 405, got %d", w.Code)
	}
}

// --- Knot graph endpoint tests ---

func TestKnotStatsMethodNotAllowed(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	req := httptest.NewRequest(http.MethodPost, "/api/v1/knot/stats", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected 405, got %d", w.Code)
	}
}

func TestKnotSearchMethodNotAllowed(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	req := httptest.NewRequest(http.MethodGet, "/api/v1/knot/search", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected 405, got %d", w.Code)
	}
}

func TestKnotContradictMethodNotAllowed(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	req := httptest.NewRequest(http.MethodGet, "/api/v1/knot/contradict", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected 405, got %d", w.Code)
	}
}

// --- LLM bridge endpoint tests ---

func TestLLMStatusMethodNotAllowed(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	req := httptest.NewRequest(http.MethodPost, "/api/v1/llm/status", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected 405, got %d", w.Code)
	}
}

func TestLLMEmbedMethodNotAllowed(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	req := httptest.NewRequest(http.MethodGet, "/api/v1/llm/embed", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected 405, got %d", w.Code)
	}
}

// --- Metrics endpoint test ---

func TestMetricsMethodNotAllowed(t *testing.T) {
	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	req := httptest.NewRequest(http.MethodPost, "/metrics", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusMethodNotAllowed {
		t.Fatalf("expected 405, got %d", w.Code)
	}
}

// --- Auth middleware test ---

func TestAuthRejectsWithoutKey(t *testing.T) {
	os.Setenv("MCP_API_KEY", "test-secret-key")
	defer os.Unsetenv("MCP_API_KEY")

	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	// Request without auth header to a protected endpoint
	req := httptest.NewRequest(http.MethodGet, "/api/v1/agents", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusUnauthorized {
		t.Fatalf("expected 401, got %d", w.Code)
	}
}

func TestAuthAllowsHealthWithoutKey(t *testing.T) {
	os.Setenv("MCP_API_KEY", "test-secret-key")
	defer os.Unsetenv("MCP_API_KEY")

	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	// /health should be exempt from auth
	req := httptest.NewRequest(http.MethodGet, "/health", nil)
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
}

func TestAuthAllowsWithCorrectKey(t *testing.T) {
	os.Setenv("MCP_API_KEY", "test-secret-key")
	defer os.Unsetenv("MCP_API_KEY")

	store, cleanup := testStore(t)
	defer cleanup()
	kernel := NewKernelBridge("/tmp/nonexistent.sock")
	router := NewRouter(store, kernel)

	req := httptest.NewRequest(http.MethodGet, "/api/v1/agents", nil)
	req.Header.Set("Authorization", "Bearer test-secret-key")
	w := httptest.NewRecorder()
	router.ServeHTTP(w, req)

	if w.Code != http.StatusOK {
		t.Fatalf("expected 200, got %d", w.Code)
	}
}
