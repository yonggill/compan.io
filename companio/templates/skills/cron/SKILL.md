# Cron Skill

Schedule reminders and recurring tasks by editing `jobs.json` directly.

## Storage

- **Path**: `~/.companio/cron/jobs.json`
- CronService auto-reloads when the file is modified (mtime check)
- Always `read_file` before editing to avoid overwriting other jobs

## Job Schema

```json
{
  "id": "8자리 UUID (uuid4()[:8])",
  "name": "짧은 설명 (30자 이내)",
  "enabled": true,
  "schedule": { ... },
  "payload": { ... },
  "state": {
    "nextRunAtMs": null,
    "lastRunAtMs": null,
    "lastStatus": null,
    "lastError": null
  },
  "createdAtMs": 1773000000000,
  "updatedAtMs": 1773000000000,
  "deleteAfterRun": false
}
```

## Schedule Types

### 1. cron (반복 — cron 표현식)
```json
"schedule": {
  "kind": "cron",
  "atMs": null,
  "everyMs": null,
  "expr": "*/30 10-20 * * *",
  "tz": "Asia/Seoul"
}
```

### 2. every (반복 — 고정 간격, 밀리초)
```json
"schedule": {
  "kind": "every",
  "atMs": null,
  "everyMs": 3600000,
  "expr": null,
  "tz": null
}
```

### 3. at (1회성 — 특정 시각, 밀리초 타임스탬프)
```json
"schedule": {
  "kind": "at",
  "atMs": 1773216000000,
  "everyMs": null,
  "expr": null,
  "tz": null
}
```
- 1회성 잡은 `"deleteAfterRun": true` 설정
- `atMs`는 **UTC 밀리초 타임스탬프** — KST 시각에서 9시간 빼서 계산
- `tz`는 `at` 방식에서 사용 불가 (cron 방식만 가능)

## Payload

```json
"payload": {
  "kind": "agent_turn",
  "message": "에이전트에게 전달할 지시사항",
  "deliver": true,
  "channel": "telegram",
  "to": "채팅 ID (문자열)",
  "metadata": {}
}
```

### 그룹 채팅 지원

그룹 채팅으로 전달할 때는 `metadata`에 `message_thread_id`를 포함:

```json
"payload": {
  "kind": "agent_turn",
  "message": "...",
  "deliver": true,
  "channel": "telegram",
  "to": "-5171625094",
  "metadata": {
    "message_thread_id": 12345
  }
}
```

- 1:1 채팅: `to`에 양수 chat_id, `metadata`는 `{}`
- 그룹 채팅: `to`에 음수 chat_id, `metadata`에 `message_thread_id` 포함 (포럼/토픽 그룹인 경우)
- 일반 그룹 (비-포럼): `metadata`는 `{}` 가능

## State

`state` 필드는 CronService가 자동 관리. 새 잡 추가 시:
```json
"state": {
  "nextRunAtMs": null,
  "lastRunAtMs": null,
  "lastStatus": null,
  "lastError": null
}
```
- `nextRunAtMs`는 `null`로 두면 CronService가 시작 시 자동 계산

## 작업 절차

### 추가
1. `read_file`로 현재 jobs.json 읽기
2. `jobs` 배열에 새 잡 추가 (id는 랜덤 8자)
3. `write_file`로 저장

### 수정
1. `read_file`로 읽기
2. 해당 id 잡 필드 수정
3. `write_file`로 저장

### 삭제
1. `read_file`로 읽기
2. 해당 id 잡을 배열에서 제거
3. `write_file`로 저장

### 비활성화/활성화
- `"enabled": false` 또는 `true` 변경

## 주의사항

- **id 중복 금지** — 기존 잡 id와 겹치지 않게
- **JSON 유효성** — 잘못된 JSON 쓰면 CronService 로드 실패
- **타임스탬프 단위**: 밀리초 (초 × 1000)
- **cron 표현식**: 표준 5필드 (분 시 일 월 요일)
- 현재 세션의 channel, chat_id는 Runtime Context에서 확인
