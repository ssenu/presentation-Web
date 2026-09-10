<script setup>
import { computed, onMounted, ref } from 'vue'
import { api } from './api'

const emit = defineEmits(['logout'])
const items = ref([])
const editing = ref(false)
const error = ref('')
const uploading = ref(false)
const upTitle = ref('')
const upCategory = ref('')
const upFile = ref(null)
const dragOverUpload = ref(false)
const dragSlug = ref(null)
const overSlug = ref(null)

// 카테고리별 그룹. 이름 있는 카테고리는 등장 순서대로, 미분류는 맨 아래.
const groups = computed(() => {
  const map = new Map()
  for (const it of items.value) {
    const key = it.category || ''
    if (!map.has(key)) map.set(key, [])
    map.get(key).push(it)
  }
  const result = [...map.entries()]
    .filter(([name]) => name !== '')
    .map(([name, list]) => ({ name, list }))
  if (map.has('')) result.push({ name: '', list: map.get('') })
  return result
})
const categories = computed(() => [...new Set(items.value.map((i) => i.category).filter(Boolean))])

async function load() {
  try {
    items.value = await api.list()
  } catch (e) {
    if (e.status === 401) emit('logout')
    else error.value = e.message
  }
}
onMounted(load)

async function run(fn) {
  error.value = ''
  try {
    await fn()
    await load()
  } catch (e) {
    if (e.status === 401) emit('logout')
    else error.value = e.message
  }
}

function pickFile(e) {
  upFile.value = e.target.files[0] || null
}
function dropFile(e) {
  dragOverUpload.value = false
  const f = e.dataTransfer.files[0]
  if (f) upFile.value = f
}
async function upload() {
  if (!upFile.value) return
  uploading.value = true
  await run(async () => {
    await api.upload(upFile.value, upTitle.value.trim(), upCategory.value.trim())
    upFile.value = null
    upTitle.value = ''
    upCategory.value = ''
  })
  uploading.value = false
}

function rename(it, e) {
  const title = e.target.value.trim()
  if (!title || title === it.title) {
    e.target.value = it.title
    return
  }
  run(() => api.patch(it.slug, { title }))
}
function recategorize(it, e) {
  const category = e.target.value.trim()
  if (category === it.category) return
  run(() => api.patch(it.slug, { category }))
}
function remove(it) {
  if (!confirm(`"${it.title}" 을(를) 삭제할까요?`)) return
  run(() => api.remove(it.slug))
}

// 드래그 정렬. 다른 카테고리 항목 위에 놓으면 그 카테고리로 이동한다.
function onDragStart(it) {
  dragSlug.value = it.slug
}
function onDragOver(it) {
  if (dragSlug.value && dragSlug.value !== it.slug) overSlug.value = it.slug
}
function onDrop(target) {
  const from = dragSlug.value
  dragSlug.value = null
  overSlug.value = null
  if (!from || from === target.slug) return
  const list = [...items.value]
  const moving = list.find((i) => i.slug === from)
  list.splice(list.indexOf(moving), 1)
  list.splice(list.indexOf(target), 0, moving)
  const categoryChanged = moving.category !== target.category
  items.value = list
  run(async () => {
    await api.reorder(list.map((i) => i.slug))
    if (categoryChanged) await api.patch(moving.slug, { category: target.category })
  })
}
function onDragEnd() {
  dragSlug.value = null
  overSlug.value = null
}

async function logout() {
  await api.logout().catch(() => {})
  emit('logout')
}
</script>

<template>
  <div class="page">
    <div class="topbar">
      <h1>발표자료</h1>
      <div style="display: flex; gap: 8px">
        <button class="ghost" :class="{ on: editing }" @click="editing = !editing">{{ editing ? '완료' : '편집' }}</button>
        <button class="ghost" @click="logout">나가기</button>
      </div>
    </div>

    <div
      v-if="editing"
      class="upload"
      :class="{ over: dragOverUpload }"
      @dragover.prevent="dragOverUpload = true"
      @dragleave="dragOverUpload = false"
      @drop.prevent="dropFile"
    >
      <div class="hint">index.html이 들어 있는 zip 파일을 끌어다 놓거나 선택하세요. 같은 제목이면 덮어씁니다.</div>
      <div class="row">
        <input type="file" accept=".zip,application/zip" @change="pickFile" />
      </div>
      <div class="row">
        <input class="field" v-model="upTitle" placeholder="제목 (비우면 파일명)" />
        <input class="field" v-model="upCategory" list="cats" placeholder="카테고리 (선택)" />
        <button class="primary" :disabled="!upFile || uploading" @click="upload">{{ uploading ? '업로드 중…' : '업로드' }}</button>
      </div>
      <div v-if="upFile" class="hint" style="margin-top: 6px">선택됨: {{ upFile.name }}</div>
    </div>
    <datalist id="cats"><option v-for="c in categories" :key="c" :value="c" /></datalist>

    <div v-if="error" class="error">{{ error }}</div>

    <div v-if="items.length === 0" class="empty">아직 발표자료가 없습니다.</div>

    <section v-for="g in groups" :key="g.name || '__none'" class="category">
      <h2 v-if="g.name">{{ g.name }}</h2>
      <div
        v-for="it in g.list"
        :key="it.slug"
        class="item"
        :class="{ dragging: dragSlug === it.slug, over: overSlug === it.slug }"
        :draggable="editing"
        @dragstart="onDragStart(it)"
        @dragover.prevent="onDragOver(it)"
        @drop.prevent="onDrop(it)"
        @dragend="onDragEnd"
      >
        <template v-if="editing">
          <span class="handle">☰</span>
          <input class="title" :value="it.title" @change="rename(it, $event)" />
          <input class="cat" :value="it.category" list="cats" placeholder="카테고리" @change="recategorize(it, $event)" />
          <button class="danger" @click="remove(it)">삭제</button>
        </template>
        <a v-else :href="`/p/${encodeURIComponent(it.slug)}/`" target="_blank" rel="noopener">{{ it.title }}</a>
      </div>
    </section>
  </div>
</template>
