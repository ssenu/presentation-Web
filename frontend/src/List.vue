<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from './api'

const emit = defineEmits(['logout'])
const items = ref([])
const error = ref('')
const notice = ref('')
const uploading = ref(false)
const fileOver = ref(false)
const editingSlug = ref(null)
const editTitle = ref('')
const editCategory = ref('')
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

// ---- 페이지 전체 드롭 업로드 ----
// 파일 드래그(OS에서 끌어온 파일)와 항목 드래그(순서 변경)를 구분한다.
function isFileDrag(e) {
  return e.dataTransfer && [...e.dataTransfer.types].includes('Files')
}
let dragDepth = 0
function onWindowDragEnter(e) {
  if (!isFileDrag(e)) return
  dragDepth++
  fileOver.value = true
}
function onWindowDragLeave(e) {
  if (!isFileDrag(e)) return
  dragDepth = Math.max(0, dragDepth - 1)
  if (dragDepth === 0) fileOver.value = false
}
function onWindowDragOver(e) {
  if (isFileDrag(e)) e.preventDefault()
}
async function onWindowDrop(e) {
  if (!isFileDrag(e)) return
  e.preventDefault()
  dragDepth = 0
  fileOver.value = false
  const files = [...e.dataTransfer.files].filter((f) => /\.zip$/i.test(f.name))
  if (files.length === 0) {
    error.value = 'zip 파일만 올릴 수 있습니다.'
    return
  }
  uploading.value = true
  notice.value = `${files.length}개 업로드 중…`
  await run(async () => {
    for (const f of files) await api.upload(f, '', '')
  })
  uploading.value = false
  notice.value = ''
}

onMounted(() => {
  load()
  window.addEventListener('dragenter', onWindowDragEnter)
  window.addEventListener('dragleave', onWindowDragLeave)
  window.addEventListener('dragover', onWindowDragOver)
  window.addEventListener('drop', onWindowDrop)
})
onBeforeUnmount(() => {
  window.removeEventListener('dragenter', onWindowDragEnter)
  window.removeEventListener('dragleave', onWindowDragLeave)
  window.removeEventListener('dragover', onWindowDragOver)
  window.removeEventListener('drop', onWindowDrop)
})

// ---- 항목 수정 / 삭제 ----
function startEdit(it) {
  editingSlug.value = it.slug
  editTitle.value = it.title
  editCategory.value = it.category
}
function cancelEdit() {
  editingSlug.value = null
}
function saveEdit(it) {
  const title = editTitle.value.trim()
  const category = editCategory.value.trim()
  editingSlug.value = null
  if (!title) return
  if (title === it.title && category === it.category) return
  run(() => api.patch(it.slug, { title, category }))
}
function remove(it) {
  if (!confirm(`"${it.title}" 을(를) 삭제할까요?`)) return
  run(() => api.remove(it.slug))
}

// ---- 드래그 정렬. 다른 카테고리 항목 위에 놓으면 그 카테고리로 이동한다. ----
function onDragStart(it, e) {
  dragSlug.value = it.slug
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', it.slug)
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
</script>

<template>
  <div class="page">
    <div class="topbar">
      <h1>발표자료</h1>
    </div>

    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="notice" class="hint">{{ notice }}</div>

    <div v-if="items.length === 0" class="empty">아직 발표자료가 없습니다.</div>

    <section v-for="g in groups" :key="g.name || '__none'" class="category">
      <h2 v-if="g.name">{{ g.name }}</h2>
      <div
        v-for="it in g.list"
        :key="it.slug"
        class="item"
        :class="{ dragging: dragSlug === it.slug, over: overSlug === it.slug, editing: editingSlug === it.slug }"
        :draggable="editingSlug !== it.slug"
        @dragstart="onDragStart(it, $event)"
        @dragover.prevent="onDragOver(it)"
        @drop.prevent.stop="onDrop(it)"
        @dragend="onDragEnd"
      >
        <template v-if="editingSlug === it.slug">
          <input class="title" v-model="editTitle" @keydown.enter="saveEdit(it)" @keydown.esc="cancelEdit" autofocus />
          <input class="cat" v-model="editCategory" list="cats" placeholder="카테고리" @keydown.enter="saveEdit(it)" @keydown.esc="cancelEdit" />
          <button class="ghost" @click="saveEdit(it)">저장</button>
          <button class="ghost" @click="cancelEdit">취소</button>
        </template>
        <template v-else>
          <a :href="`/p/${encodeURIComponent(it.slug)}/`" target="_blank" rel="noopener">{{ it.title }}</a>
          <span class="actions">
            <button class="ghost" @click="startEdit(it)">수정</button>
            <button class="danger" @click="remove(it)">삭제</button>
          </span>
        </template>
      </div>
    </section>
    <datalist id="cats"><option v-for="c in categories" :key="c" :value="c" /></datalist>

    <p class="hint footer">zip 파일을 이 화면에 끌어다 놓으면 업로드됩니다. 같은 이름이면 덮어쓰고, 항목을 끌어서 순서와 카테고리를 바꿀 수 있습니다.</p>

    <div v-if="fileOver" class="dropzone">
      <div>{{ uploading ? '업로드 중…' : '여기에 놓으면 업로드됩니다' }}</div>
    </div>
  </div>
</template>
