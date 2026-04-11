# API 路径审计

- 后端路由数: 165
- 前端 fetch 数: 156

## 后端路由

```
DELETE /api/sessions/{session_id}
DELETE /api/sessions/{session_id}/messages/{message_id}
DELETE /api/task-queue/scheduled-tasks/{schedule_id}
DELETE /api/task-queue/tasks/{task_id}
GET /api/audit/report
GET /api/audit/summary
GET /api/chat/article
GET /api/chat/article/metadata
GET /api/chat/article/revisions
GET /api/chat/mw-sources
GET /api/heartbeat/status
GET /api/home-briefing/latest
GET /api/latex/render
GET /api/mediawiki/base-url
GET /api/mediawiki/diagnostic
GET /api/mediawiki/pages/{title:path}
GET /api/mediawiki/random-read
GET /api/mediawiki/recent-read
GET /api/mediawiki/search
GET /api/mediawiki/search-read
GET /api/mediawiki/sync/status
GET /api/mediawiki/test-connection
GET /api/models/selectable
GET /api/network/audit/env
GET /api/network/audit/history
GET /api/network/audit/targets
GET /api/pdf/page-range-text
GET /api/pdf/page-range-vision
GET /api/pdf/page-text
GET /api/pdf/page-vision
GET /api/pdf/view
GET /api/ppt-assistant/run-status
GET /api/ppt-assistant/slide-images/file/{job_id}/{page_index}
GET /api/search/availability
GET /api/search/files
GET /api/search/unified
GET /api/sessions/list
GET /api/sessions/search
GET /api/sessions/{session_id}
GET /api/settings/kanban/board
GET /api/settings/kanban/boards
GET /api/settings/kanban/status
GET /api/settings/llm-audit/daily-stats
GET /api/settings/llm-audit/dates
GET /api/settings/llm-audit/list
GET /api/settings/model-availability-audit/models
GET /api/settings/model-config-audit
GET /api/settings/model-stats
GET /api/settings/system-prompt-audit/prompts
GET /api/settings/tavily-audit/path
GET /api/settings/tavily-audit/stats
GET /api/settings/work-config
GET /api/settings/writing-profile
GET /api/settings/writing-profile/acceptance-records
GET /api/settings/writing-profile/acceptance-records/{record_id}/sections
GET /api/storage/audit
GET /api/storage/config
GET /api/system/cpu
GET /api/system/disk
GET /api/system/disk-scan-report
GET /api/system/load
GET /api/system/memory
GET /api/system/network
GET /api/system/processes
GET /api/task-queue/debug
GET /api/task-queue/scheduled-tasks
GET /api/task-queue/scheduled-tasks/{schedule_id}
GET /api/task-queue/task-types
GET /api/task-queue/task-types/{task_type}
GET /api/task-queue/task-types/{task_type}/linkable-upstreams
GET /api/task-queue/tasks
GET /api/task-queue/tasks/{task_id}
GET /api/task-queue/tasks/{task_id}/output-file
GET /api/task-queue/tasks/{task_id}/queue-status
GET /api/task-queue/workers
GET /api/tasks
GET /api/tasks/{task_id}
GET /api/tests/history
GET /api/tests/history/{run_id}
GET /api/tests/list
GET /api/tests/statistics
GET /api/tests/status
GET /api/tools/list
GET /api/version
GET /api/web-reader/inline-static/{filename}
GET /api/wechat-mp/cover-image
GET /api/wechat-mp/drafts
GET /api/wechat-mp/drafts/detail
GET /api/wechat-mp/materials/images
GET /api/wechat-mp/outbound-ip
GET /api/wikipedia/base-url
GET /api/wikipedia/diagnostic
GET /api/wikipedia/pages/{title:path}
GET /api/wikipedia/random-read
GET /api/wikipedia/recent-read
GET /api/wikipedia/search-read
PATCH /api/sessions/{session_id}
PATCH /api/task-queue/scheduled-tasks/{schedule_id}
PATCH /api/task-queue/tasks/{task_id}
PATCH /api/task-queue/tasks/{task_id}/patch-result-output-file
POST /api/ai-hot-news/run
POST /api/chat
POST /api/chat/article/apply-patch
POST /api/chat/article/generate-cover-images
POST /api/chat/article/generate-cover-prompt
POST /api/chat/article/generate-metadata
POST /api/chat/article/merge
POST /api/chat/article/patch
POST /api/chat/article/restore
POST /api/chat/article/upload-cover-to-wechat
POST /api/chat/rate-message
POST /api/chat/stream
POST /api/execution/approve
POST /api/execution/reject
POST /api/gvim/open-mediawiki-page
POST /api/home-briefing/generate
POST /api/mediawiki/pages/{title:path}
POST /api/mediawiki/parse
POST /api/mediawiki/reset-client
POST /api/mediawiki/sync
POST /api/mediawiki/upload-image
POST /api/mediawiki/upload-image-file
POST /api/network/audit/run
POST /api/pdf/resolve
POST /api/pdf/upload-from-extension
POST /api/ppt-assistant/deck
POST /api/ppt-assistant/export-pptx
POST /api/ppt-assistant/extract
POST /api/ppt-assistant/refine
POST /api/ppt-assistant/run
POST /api/ppt-assistant/run-stream
POST /api/ppt-assistant/slide-images/stream
POST /api/sessions
POST /api/sessions/batch-delete
POST /api/sessions/{session_id}/clear
POST /api/sessions/{session_id}/messages/batch-delete
POST /api/sessions/{session_id}/summary
POST /api/settings/model-availability-audit/probe
POST /api/settings/writing-profile/learn-from-ratings
POST /api/settings/writing-profile/rate-section
POST /api/storage/audit/cleanup-tmp-dbs
POST /api/task-queue/cleanup
POST /api/task-queue/scheduled-tasks
POST /api/task-queue/scheduled-tasks/{schedule_id}/run-now
POST /api/task-queue/tasks
POST /api/task-queue/tasks/{task_id}/cancel
POST /api/task-queue/tasks/{task_id}/requeue
POST /api/task-queue/tasks/{task_id}/restart
POST /api/task-queue/tasks/{task_id}/restore
POST /api/task-queue/tasks/{task_id}/soft-delete
POST /api/task-queue/upload-input-file
POST /api/tasks/{task_id}/cancel
POST /api/tests/run
POST /api/web-reader/fetch-weread-inline-image
POST /api/web-reader/materialize-inline-images
POST /api/web-reader/ocr
POST /api/web-reader/summarize
POST /api/wechat-mp/upload-article-image
POST /api/wechat-mp/upload-cover
POST /api/wikipedia/parse
PUT /api/chat/article
PUT /api/chat/mw-sources
PUT /api/settings/work-config
PUT /api/settings/writing-profile
PUT /api/task-queue/scheduled-tasks/{schedule_id}/toggle
```

## 前端调用的 API

- DELETE /api/task-queue/scheduled-tasks/${task.schedule_id}
- DELETE /api/task-queue/tasks/${taskId}
- GET /api/ai-hot-news/run
- GET /api/audit/report
- GET /api/chat/article
- GET /api/chat/article/apply-patch
- GET /api/chat/article/generate-cover-images
- GET /api/chat/article/generate-cover-prompt
- GET /api/chat/article/generate-metadata
- GET /api/chat/article/metadata
- GET /api/chat/article/patch
- GET /api/chat/article/restore
- GET /api/chat/article/revisions
- GET /api/chat/article/upload-cover-to-wechat
- GET /api/chat/mw-sources
- GET /api/chat/rate-message
- GET /api/chat/stream
- GET /api/heartbeat/status
- GET /api/home-briefing/generate
- GET /api/home-briefing/latest
- GET /api/latex/render
- GET /api/mediawiki/base-url
- GET /api/mediawiki/pages/
- GET /api/mediawiki/random-read
- GET /api/mediawiki/recent-read
- GET /api/mediawiki/search
- GET /api/mediawiki/search-read
- GET /api/mediawiki/upload-image
- GET /api/mediawiki/upload-image-file
- GET /api/models/selectable
- GET /api/network/audit/env
- GET /api/network/audit/history
- GET /api/network/audit/run
- GET /api/network/audit/targets
- GET /api/pdf/page-range-text
- GET /api/pdf/resolve
- GET /api/pdf/upload-from-extension
- GET /api/ppt-assistant/deck
- GET /api/ppt-assistant/export-pptx
- GET /api/ppt-assistant/extract
- GET /api/ppt-assistant/refine
- GET /api/ppt-assistant/run
- GET /api/ppt-assistant/run-status
- GET /api/ppt-assistant/run-stream
- GET /api/ppt-assistant/slide-images/stream
- GET /api/sessions
- GET /api/sessions/
- GET /api/sessions/batch-delete
- GET /api/sessions/list
- GET /api/settings/kanban/board
- GET /api/settings/kanban/boards
- GET /api/settings/llm-audit/daily-stats
- GET /api/settings/llm-audit/dates
- GET /api/settings/llm-audit/list
- GET /api/settings/model-availability-audit/models
- GET /api/settings/model-availability-audit/probe
- GET /api/settings/model-config-audit
- GET /api/settings/model-stats
- GET /api/settings/system-prompt-audit/prompts
- GET /api/settings/work-config
- GET /api/settings/writing-profile
- GET /api/settings/writing-profile/acceptance-records
- GET /api/settings/writing-profile/acceptance-records/${selectedRecordId}/sections
- GET /api/settings/writing-profile/acceptance-records//sections
- GET /api/settings/writing-profile/learn-from-ratings
- GET /api/settings/writing-profile/rate-section
- GET /api/storage/audit
- GET /api/storage/audit/cleanup-tmp-dbs
- GET /api/system/disk
- GET /api/system/disk-scan-report
- GET /api/task-queue/cleanup
- GET /api/task-queue/scheduled-tasks
- GET /api/task-queue/scheduled-tasks/${task.schedule_id}
- GET /api/task-queue/scheduled-tasks/${task.schedule_id}/run-now
- GET /api/task-queue/scheduled-tasks/${task.schedule_id}/toggle
- GET /api/task-queue/task-types
- GET /api/task-queue/task-types//linkable-upstreams
- GET /api/task-queue/tasks
- GET /api/task-queue/tasks/
- GET /api/task-queue/tasks/${task.task_id}/patch-result-output-file
- GET /api/task-queue/tasks/${task.task_id}/requeue
- GET /api/task-queue/tasks/${taskId}
- GET /api/task-queue/tasks/${taskId}/cancel
- GET /api/task-queue/tasks/${taskId}/output-file
- GET /api/task-queue/tasks/${taskId}/queue-status
- GET /api/task-queue/tasks/${taskId}/restart
- GET /api/task-queue/tasks/${taskId}/restore
- GET /api/task-queue/tasks/${taskId}/soft-delete
- GET /api/task-queue/tasks//output-file
- GET /api/task-queue/tasks//queue-status
- GET /api/task-queue/upload-input-file
- GET /api/tools/list
- GET /api/version
- GET /api/web-reader/summarize
- GET /api/wechat-mp/drafts
- GET /api/wechat-mp/drafts/detail
- GET /api/wechat-mp/materials/images
- GET /api/wechat-mp/outbound-ip
- GET /api/wechat-mp/upload-article-image
- GET /api/wechat-mp/upload-cover
- GET /api/wikipedia/pages/
- GET /api/wikipedia/random-read
- GET /api/wikipedia/recent-read
- GET /api/wikipedia/search-read
- GET /api/writing-suggestions
- PATCH /api/task-queue/scheduled-tasks/${task.schedule_id}
- PATCH /api/task-queue/tasks/${task.task_id}/patch-result-output-file
- PATCH /api/task-queue/tasks/${taskId}
- POST /api/ai-hot-news/run
- POST /api/chat/article/apply-patch
- POST /api/chat/article/generate-cover-images
- POST /api/chat/article/generate-cover-prompt
- POST /api/chat/article/generate-metadata
- POST /api/chat/article/patch
- POST /api/chat/article/restore
- POST /api/chat/article/upload-cover-to-wechat
- POST /api/chat/rate-message
- POST /api/chat/stream
- POST /api/home-briefing/generate
- POST /api/mediawiki/upload-image
- POST /api/mediawiki/upload-image-file
- POST /api/network/audit/run
- POST /api/pdf/resolve
- POST /api/pdf/upload-from-extension
- POST /api/ppt-assistant/deck
- POST /api/ppt-assistant/export-pptx
- POST /api/ppt-assistant/extract
- POST /api/ppt-assistant/refine
- POST /api/ppt-assistant/run
- POST /api/ppt-assistant/run-stream
- POST /api/ppt-assistant/slide-images/stream
- POST /api/sessions
- POST /api/sessions/batch-delete
- POST /api/settings/model-availability-audit/probe
- POST /api/settings/writing-profile/learn-from-ratings
- POST /api/settings/writing-profile/rate-section
- POST /api/storage/audit/cleanup-tmp-dbs
- POST /api/task-queue/cleanup
- POST /api/task-queue/scheduled-tasks
- POST /api/task-queue/scheduled-tasks/${task.schedule_id}/run-now
- POST /api/task-queue/tasks
- POST /api/task-queue/tasks/${task.task_id}/requeue
- POST /api/task-queue/tasks/${taskId}/cancel
- POST /api/task-queue/tasks/${taskId}/restart
- POST /api/task-queue/tasks/${taskId}/restore
- POST /api/task-queue/tasks/${taskId}/soft-delete
- POST /api/task-queue/upload-input-file
- POST /api/web-reader/summarize
- POST /api/wechat-mp/upload-article-image
- POST /api/wechat-mp/upload-cover
- POST /api/writing-suggestions
- PUT /api/chat/article
- PUT /api/chat/mw-sources
- PUT /api/settings/work-config
- PUT /api/settings/writing-profile
- PUT /api/task-queue/scheduled-tasks/${task.schedule_id}/toggle

## 后端有但前端未使用

- /api/audit/summary
- /api/chat
- /api/chat/article/merge
- /api/execution/approve
- /api/execution/reject
- /api/gvim/open-mediawiki-page
- /api/mediawiki/diagnostic
- /api/mediawiki/pages/{id}
- /api/mediawiki/parse
- /api/mediawiki/reset-client
- /api/mediawiki/sync
- /api/mediawiki/sync/status
- /api/mediawiki/test-connection
- /api/pdf/page-range-vision
- /api/pdf/page-text
- /api/pdf/page-vision
- /api/pdf/view
- /api/ppt-assistant/slide-images/file/{id}/{id}
- /api/search/availability
- /api/search/files
- /api/search/unified
- /api/sessions/search
- /api/sessions/{id}
- /api/sessions/{id}/clear
- /api/sessions/{id}/messages/batch-delete
- /api/sessions/{id}/messages/{id}
- /api/sessions/{id}/summary
- /api/settings/kanban/status
- /api/settings/tavily-audit/path
- /api/settings/tavily-audit/stats
- /api/settings/writing-profile/acceptance-records/{id}/sections
- /api/storage/config
- /api/system/cpu
- /api/system/load
- /api/system/memory
- /api/system/network
- /api/system/processes
- /api/task-queue/debug
- /api/task-queue/scheduled-tasks/{id}
- /api/task-queue/scheduled-tasks/{id}/run-now
- /api/task-queue/scheduled-tasks/{id}/toggle
- /api/task-queue/task-types/{id}
- /api/task-queue/task-types/{id}/linkable-upstreams
- /api/task-queue/tasks/{id}
- /api/task-queue/tasks/{id}/cancel
- /api/task-queue/tasks/{id}/output-file
- /api/task-queue/tasks/{id}/patch-result-output-file
- /api/task-queue/tasks/{id}/queue-status
- /api/task-queue/tasks/{id}/requeue
- /api/task-queue/tasks/{id}/restart
- /api/task-queue/tasks/{id}/restore
- /api/task-queue/tasks/{id}/soft-delete
- /api/task-queue/workers
- /api/tasks
- /api/tasks/{id}
- /api/tasks/{id}/cancel
- /api/tests/history
- /api/tests/history/{id}
- /api/tests/list
- /api/tests/run
- /api/tests/statistics
- /api/tests/status
- /api/web-reader/fetch-weread-inline-image
- /api/web-reader/inline-static/{id}
- /api/web-reader/materialize-inline-images
- /api/web-reader/ocr
- /api/wechat-mp/cover-image
- /api/wikipedia/base-url
- /api/wikipedia/diagnostic
- /api/wikipedia/pages/{id}
- /api/wikipedia/parse

## 前端调用但可能未实现（需人工核对）

- /api/mediawiki/pages/
- /api/sessions/
- /api/settings/writing-profile/acceptance-records/${id}/sections
- /api/settings/writing-profile/acceptance-records//sections
- /api/task-queue/scheduled-tasks/${id}
- /api/task-queue/scheduled-tasks/${id}/run-now
- /api/task-queue/scheduled-tasks/${id}/toggle
- /api/task-queue/task-types//linkable-upstreams
- /api/task-queue/tasks/
- /api/task-queue/tasks/${id}
- /api/task-queue/tasks/${id}/cancel
- /api/task-queue/tasks/${id}/output-file
- /api/task-queue/tasks/${id}/patch-result-output-file
- /api/task-queue/tasks/${id}/queue-status
- /api/task-queue/tasks/${id}/requeue
- /api/task-queue/tasks/${id}/restart
- /api/task-queue/tasks/${id}/restore
- /api/task-queue/tasks/${id}/soft-delete
- /api/task-queue/tasks//output-file
- /api/task-queue/tasks//queue-status
- /api/wikipedia/pages/
- /api/writing-suggestions