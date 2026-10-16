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
      from sqlalchemy import text
      from app.database import engine
      for attempt in range(120):
          try:
              with engine.connect() as connection:
                  connection.execute(text("SELECT 1 FROM products LIMIT 1"))
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
