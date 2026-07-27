package api

import (
    "fmt"
    "log"
    "net/http"
    "path/filepath"
    "examsystem/internal/config"
    "examsystem/internal/engine"
    "examsystem/internal/logger"
    "examsystem/internal/storage"
)

type Server struct {
    Engine  *engine.Engine
    Storage *storage.Storage
    Config  *config.Config
    Handler *Handler
}

func NewServer(cfg *config.Config) *Server {
    stg := storage.New(cfg.Data.Path)
    eng := engine.New()
    sessionsDir := cfg.Data.SessionDir
    if sessionsDir == "" {
        sessionsDir = filepath.Join(filepath.Dir(cfg.Data.Path), "sessions")
    }
    sm := engine.NewSessionManager(eng, sessionsDir)
    handler := NewHandler(eng, stg, sm, cfg)
    return &Server{
        Engine:  eng,
        Storage: stg,
        Config:  cfg,
        Handler: handler,
    }
}

func recoveryMiddleware(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        defer func() {
            if err := recover(); err != nil {
                log.Printf("PANIC in %s %s: %v", r.Method, r.URL.Path, err)
                http.Error(w, "Internal Server Error: "+fmt.Sprint(err), http.StatusInternalServerError)
            }
        }()
        next.ServeHTTP(w, r)
    })
}

func (s *Server) Start() error {
    mux := http.NewServeMux()
    s.Handler.RegisterRoutes(mux)
    addr := fmt.Sprintf(":%d", s.Config.Server.Port)
    logger.Info.Printf("Starting exam system server on %s", addr)
    return http.ListenAndServe(addr, recoveryMiddleware(mux))
}
