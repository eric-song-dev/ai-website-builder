import { useEffect, useMemo, useRef, useState } from "react";
import {
  ArrowRight,
  Check,
  ChevronDown,
  Code2,
  Download,
  ExternalLink,
  FileCode2,
  Globe2,
  LoaderCircle,
  MousePointer2,
  Play,
  Plus,
  Rocket,
  Sparkles,
  WandSparkles,
  X,
} from "lucide-react";
import { api, type Job, type Mode, type Project, type SiteFile } from "./api";

const eventNames = [
  "job.started",
  "agent.started",
  "agent.completed",
  "asset.completed",
  "artifact.patch",
  "artifact.ready",
  "job.completed",
  "job.failed",
];
const modeLabels: Record<Mode, string> = {
  single_html: "Single HTML",
  multi_page: "Multi-page",
  react: "React / Vite",
};
type TimelineEvent = {
  id: string;
  name: string;
  data: Record<string, unknown>;
  time: string;
};
type Selection = { selector: string; text: string; path: string };

function App() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const [files, setFiles] = useState<SiteFile[]>([]);
  const [activeFile, setActiveFile] = useState("");
  const [events, setEvents] = useState<TimelineEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [showCreate, setShowCreate] = useState(false);
  const [selection, setSelection] = useState<Selection | null>(null);
  const [revision, setRevision] = useState("");
  const [deployUrl, setDeployUrl] = useState("");
  const [viewport, setViewport] = useState<"desktop" | "tablet" | "mobile">(
    "desktop",
  );
  const sourceRef = useRef<EventSource | null>(null);

  const loadProjects = async () => {
    const value = await api.projects();
    setProjects(value);
    if (!project && value[0]) await openProject(value[0]);
  };
  const openProject = async (value: Project, preserveEvents = false) => {
    setProject(value);
    if (!preserveEvents) setEvents([]);
    setSelection(null);
    setDeployUrl("");
    const result = await api.files(value.id);
    setFiles(result.files);
    setActiveFile(result.files[0]?.path || "");
  };
  useEffect(() => {
    loadProjects().catch((e) => setError(e.message));
    return () => sourceRef.current?.close();
  }, []);
  useEffect(() => {
    const receive = (event: MessageEvent) => {
      if (event.data?.type === "builder:select") setSelection(event.data);
    };
    window.addEventListener("message", receive);
    return () => window.removeEventListener("message", receive);
  }, []);

  const follow = (job: Job) => {
    sourceRef.current?.close();
    setBusy(true);
    setEvents([]);
    const source = new EventSource(`/api/jobs/${job.id}/events`);
    sourceRef.current = source;
    eventNames.forEach((name) =>
      source.addEventListener(name, async (event) => {
        const message = event as MessageEvent;
        let data = {};
        try {
          data = JSON.parse(message.data);
        } catch {}
        setEvents((current) => [
          ...current,
          {
            id: message.lastEventId || crypto.randomUUID(),
            name,
            data,
            time: new Date().toLocaleTimeString(),
          },
        ]);
        if (name === "job.completed") {
          source.close();
          setBusy(false);
          const fresh = await api.project(job.project_id);
          await openProject(fresh, true);
          await loadProjects();
        }
        if (name === "job.failed") {
          source.close();
          setBusy(false);
          setError(
            String((data as { error?: string }).error || "Generation failed"),
          );
        }
      }),
    );
  };
  const generate = async () => {
    if (!project) return;
    setError("");
    try {
      follow(await api.generate(project.id));
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const revise = async () => {
    if (!project || !revision.trim()) return;
    setError("");
    try {
      follow(await api.revise(project.id, revision, selection));
      setRevision("");
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const deploy = async () => {
    if (!project) return;
    setError("");
    try {
      setDeployUrl((await api.deploy(project.id)).url);
    } catch (e) {
      setError((e as Error).message);
    }
  };
  const selectedFile = files.find((file) => file.path === activeFile);
  const preview = project?.active_version
    ? `/api/projects/${project.id}/preview/index.html?v=${project.active_version}`
    : "";

  return (
    <div className="app-shell">
      <header className="topbar">
        <button className="wordmark" onClick={() => setProject(null)}>
          <span className="mark">
            <Sparkles size={17} />
          </span>
          <span>FOUNDRY</span>
          <small>AI SITE STUDIO</small>
        </button>
        <div className="project-switcher">
          <span className="status-dot" />
          {project?.name || "No project selected"}
          <ChevronDown size={15} />
          <select
            aria-label="Select project"
            value={project?.id || ""}
            onChange={(e) => {
              const next = projects.find((p) => p.id === e.target.value);
              if (next) openProject(next);
            }}
          >
            <option value="">Choose a project</option>
            {projects.map((p) => (
              <option value={p.id} key={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>
        <div className="top-actions">
          <button className="ghost" onClick={() => setShowCreate(true)}>
            <Plus size={16} /> New project
          </button>
          {project?.active_version && (
            <>
              <a className="ghost" href={`/api/projects/${project.id}/export`}>
                <Download size={16} /> Export
              </a>
              <button className="primary small" onClick={deploy}>
                <Rocket size={16} /> Deploy
              </button>
            </>
          )}
        </div>
      </header>
      {!project ? (
        <Empty onCreate={() => setShowCreate(true)} />
      ) : (
        <main className="workspace">
          <aside className="left-panel">
            <div className="panel-heading">
              <span>BUILD BRIEF</span>
              <span className="mode-chip">{modeLabels[project.mode]}</span>
            </div>
            <div className="brief">
              <h1>{project.name}</h1>
              <p>{project.prompt}</p>
              <button
                className="primary generate"
                disabled={busy}
                onClick={generate}
              >
                {busy ? (
                  <LoaderCircle className="spin" size={18} />
                ) : (
                  <WandSparkles size={18} />
                )}{" "}
                {project.active_version
                  ? "Regenerate site"
                  : "Generate website"}
                <ArrowRight size={17} />
              </button>
            </div>
            <div className="timeline">
              <div className="panel-heading">
                <span>AGENT ACTIVITY</span>
                <span>{events.length}</span>
              </div>
              {events.length === 0 ? (
                <div className="timeline-empty">
                  <Play size={17} />
                  <p>
                    The Planner, four asset pipelines, Generator, and Reviewer
                    will report here.
                  </p>
                </div>
              ) : (
                events.map((event, index) => (
                  <div className="event" key={event.id + index}>
                    <span
                      className={`event-icon ${event.name.includes("completed") || event.name.includes("ready") ? "done" : ""}`}
                    >
                      {event.name.includes("completed") ||
                      event.name.includes("ready") ? (
                        <Check size={12} />
                      ) : (
                        <span />
                      )}
                    </span>
                    <div>
                      <strong>{event.name.replace(".", " / ")}</strong>
                      <p>
                        {String(
                          event.data.agent ||
                            event.data.pipeline ||
                            event.data.status ||
                            event.data.file_count ||
                            "",
                        )}
                      </p>
                    </div>
                    <time>{event.time}</time>
                  </div>
                ))
              )}
            </div>
          </aside>
          <section className="canvas">
            <div className="canvas-bar">
              <div>
                <Globe2 size={16} />
                <span>Live preview</span>
                {project.active_version && (
                  <span className="version">
                    VERSION {project.active_version}
                  </span>
                )}
              </div>
              <div className="viewport-tabs">
                {(["desktop", "tablet", "mobile"] as const).map((size) => (
                  <button
                    key={size}
                    className={viewport === size ? "active" : ""}
                    onClick={() => setViewport(size)}
                  >
                    {size[0].toUpperCase() + size.slice(1)}
                  </button>
                ))}
              </div>
            </div>
            {preview ? (
              <div className={`browser-frame ${viewport}`}>
                <div className="browser-chrome">
                  <div className="traffic">
                    <i />
                    <i />
                    <i />
                  </div>
                  <div className="address">
                    <span>Preview</span> /{" "}
                    {project.name.toLowerCase().replaceAll(" ", "-")}
                  </div>
                  <ExternalLink size={14} />
                </div>
                <iframe
                  title="Generated website preview"
                  sandbox="allow-scripts allow-forms allow-popups"
                  src={preview}
                />
              </div>
            ) : (
              <div className="preview-empty">
                <div className="orb">
                  <Sparkles />
                </div>
                <h2>Your next website starts here.</h2>
                <p>
                  Generate the brief to watch four asset pipelines and three
                  specialized agents build in parallel.
                </p>
                <button className="primary" onClick={generate}>
                  <WandSparkles size={18} /> Generate website
                </button>
              </div>
            )}
            {selection && (
              <div className="selection-pill">
                <MousePointer2 size={15} />
                <span>
                  <strong>{selection.selector}</strong>
                  {selection.text}
                </span>
                <button
                  aria-label="Clear selection"
                  onClick={() => setSelection(null)}
                >
                  <X size={15} />
                </button>
              </div>
            )}
          </section>
          <aside className="right-panel">
            <div className="tabs">
              <button className="active">
                <FileCode2 size={15} /> Files
              </button>
              <button>
                <Code2 size={15} /> Inspector
              </button>
            </div>
            <div className="files">
              {files.map((file) => (
                <button
                  className={file.path === activeFile ? "active" : ""}
                  key={file.path}
                  onClick={() => setActiveFile(file.path)}
                >
                  <FileCode2 size={14} />
                  <span>{file.path}</span>
                  <small>{Math.max(1, Math.round(file.bytes / 1024))}kb</small>
                </button>
              ))}
            </div>
            <div className="code">
              <div className="code-head">
                <span>{activeFile || "No file"}</span>
                <small>{selectedFile?.sha256.slice(0, 7)}</small>
              </div>
              <pre>
                <code>
                  {selectedFile?.content ||
                    "Generate a site to inspect its source."}
                </code>
              </pre>
            </div>
            <div className="revision">
              <div className="panel-heading">
                <span>QUICK REVISION</span>
              </div>
              {selection && (
                <div className="selected-context">
                  <MousePointer2 size={14} />
                  <span>{selection.text || selection.selector}</span>
                </div>
              )}
              <textarea
                value={revision}
                onChange={(e) => setRevision(e.target.value)}
                placeholder="Try: Make the selected section darker and more concise…"
              />
              <button
                className="primary"
                disabled={busy || !project.active_version || !revision.trim()}
                onClick={revise}
              >
                <Sparkles size={16} /> Apply revision
              </button>
            </div>
          </aside>
        </main>
      )}
      {error && (
        <div className="toast error">
          <X size={17} />
          <span>{error}</span>
          <button onClick={() => setError("")}>Dismiss</button>
        </div>
      )}
      {deployUrl && (
        <div className="toast success">
          <Rocket size={17} />
          <span>Published successfully</span>
          <a href={deployUrl} target="_blank">
            Open site <ExternalLink size={14} />
          </a>
        </div>
      )}
      {showCreate && (
        <CreateModal
          onClose={() => setShowCreate(false)}
          onCreate={async (body) => {
            const created = await api.create(body);
            setShowCreate(false);
            setProjects((current) => [created, ...current]);
            await openProject(created);
            follow(await api.generate(created.id));
          }}
        />
      )}
    </div>
  );
}

function Empty({ onCreate }: { onCreate: () => void }) {
  return (
    <main className="empty">
      <div className="orb">
        <Sparkles />
      </div>
      <div className="eyebrow">MULTI-AGENT CREATIVE SYSTEM</div>
      <h1>
        From a sentence
        <br />
        to a living website.
      </h1>
      <p>
        Plan, design, review, revise, export, and publish—all from one focused
        workspace.
      </p>
      <button className="primary" onClick={onCreate}>
        <Plus size={18} /> Create your first project
      </button>
    </main>
  );
}

function CreateModal({
  onClose,
  onCreate,
}: {
  onClose: () => void;
  onCreate: (value: {
    name: string;
    prompt: string;
    mode: Mode;
  }) => Promise<void>;
}) {
  const [name, setName] = useState("Atlas Studio");
  const [prompt, setPrompt] = useState(
    "A confident, editorial landing page for a product design studio that helps ambitious teams launch clearer digital products.",
  );
  const [mode, setMode] = useState<Mode>("single_html");
  const [saving, setSaving] = useState(false);
  return (
    <div
      className="modal-backdrop"
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <form
        className="modal"
        onSubmit={async (e) => {
          e.preventDefault();
          setSaving(true);
          await onCreate({ name, prompt, mode }).finally(() =>
            setSaving(false),
          );
        }}
      >
        <div className="modal-head">
          <div>
            <span className="eyebrow">NEW BUILD</span>
            <h2>What should we make?</h2>
          </div>
          <button type="button" onClick={onClose}>
            <X />
          </button>
        </div>
        <label>
          Project name
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            maxLength={120}
          />
        </label>
        <label>
          Website brief
          <textarea
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            required
            minLength={10}
          />
        </label>
        <fieldset>
          <legend>Code mode</legend>
          <div className="mode-grid">
            {(Object.keys(modeLabels) as Mode[]).map((value) => (
              <button
                type="button"
                className={mode === value ? "active" : ""}
                onClick={() => setMode(value)}
                key={value}
              >
                <strong>{modeLabels[value]}</strong>
                <small>
                  {value === "single_html"
                    ? "Portable zero-build page"
                    : value === "multi_page"
                      ? "Linked static site"
                      : "Fixed, safe Vite shell"}
                </small>
              </button>
            ))}
          </div>
        </fieldset>
        <button className="primary modal-submit" disabled={saving}>
          {saving ? <LoaderCircle className="spin" /> : <Sparkles />} Create &
          generate
        </button>
      </form>
    </div>
  );
}
export default App;
