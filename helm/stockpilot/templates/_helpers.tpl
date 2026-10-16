{{- define "stockpilot.labels" -}}
app.kubernetes.io/name: stockpilot
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
helm.sh/chart: {{ .Chart.Name }}-{{ .Chart.Version }}
{{- end }}
{{- define "stockpilot.security" -}}
allowPrivilegeEscalation: false
readOnlyRootFilesystem: true
capabilities:
  drop: [ALL]
{{- end }}
{{- define "stockpilot.env" -}}
- configMapRef:
    name: stockpilot-config
- secretRef:
    name: {{ .Values.secrets.existingSecret }}
{{- end }}
{{- define "stockpilot.waitSchema" -}}
- name: wait-for-schema
  image: "{{ .Values.backend.image.repository }}:{{ .Values.backend.image.tag }}"
  imagePullPolicy: {{ .Values.backend.image.pullPolicy }}
  command: [python, -c]
  args:
    - |
      import time
      from alembic.config import Config
      from alembic.runtime.migration import MigrationContext
      from alembic.script import ScriptDirectory
      from app.database import engine
      expected_heads = set(ScriptDirectory.from_config(Config("alembic.ini")).get_heads())
      for attempt in range(120):
          try:
              with engine.connect() as connection:
                  current_heads = set(MigrationContext.configure(connection).get_current_heads())
                  if current_heads != expected_heads:
                      raise RuntimeError("Database schema does not match this application release")
              break
          except Exception:
              time.sleep(2)
      else:
          raise SystemExit("Database migrations did not become ready")
  envFrom:
    {{- include "stockpilot.env" . | nindent 4 }}
  securityContext:
    {{- include "stockpilot.security" . | nindent 4 }}
  resources:
    requests: {cpu: 50m, memory: 64Mi}
    limits: {cpu: 500m, memory: 256Mi}
{{- end }}
