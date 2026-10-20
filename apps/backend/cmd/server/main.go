// Program server menjalankan API PulseSure Edge.
package main

import (
	"log"
	"net/http"
	"os"
	"strings"
	"time"

	"pulsesure/backend/internal/ai"
	"pulsesure/backend/internal/api"
	"pulsesure/backend/internal/history"
	"pulsesure/backend/internal/model"
	"pulsesure/backend/internal/store"
)

func env(kunci, def string) string {
	if v := os.Getenv(kunci); v != "" {
		return v
	}
	return def
}

func main() {
	st, err := store.Load(env("DATA_DIR", "data"))
	if err != nil {
		log.Fatalf("failed to load data: %v", err)
	}

	mdl, err := model.LoadDummy(env("MODEL_PATH", "models/dummy_model.json"))
	if err != nil {
		log.Fatalf("failed to load dummy model: %v", err)
	}

	var repo history.Repo
	if os.Getenv("USE_MEMORY") == "1" {
		log.Println("USE_MEMORY=1: history is stored in memory and will be lost when the server stops")
		repo = history.NewMemory()
	} else {
		pg, err := history.OpenPostgres(env("DATABASE_URL",
			"postgres://pulsesure:pulsesure@localhost:5433/pulsesure?sslmode=disable"))
		if err != nil {
			log.Fatalf("%v", err)
		}
		repo = pg
	}

	origins := strings.Split(env("CORS_ORIGIN", "http://localhost:5173"), ",")

	var aiClient *ai.Client
	if u := env("AI_SERVICE_URL", ""); u != "" {
		aiClient = ai.NewClient(u, 20*time.Second)
		log.Printf("AI service: %s", u)
	}
	activeModelName := mdl.ModelName
	activeModelVersion := mdl.ModelVersion
	if aiClient != nil {
		activeModelName = ai.ModelName
		activeModelVersion = "reported per inference"
	}
	srv := &http.Server{
		Addr:         env("ADDR", ":8080"),
		Handler:      api.NewServerWithAI(st, mdl, repo, origins, aiClient),
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 60 * time.Second,
	}

	log.Printf("PulseSure backend is running at %s (sessions: %d, model: %s %s)",
		srv.Addr, len(st.List()), activeModelName, activeModelVersion)
	log.Fatal(srv.ListenAndServe())
}
