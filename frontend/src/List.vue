<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { api } from './api'

const emit = defineEmits(['logout'])
const items = ref([])
const categoryNames = ref([])
const error = ref('')
const notice = ref('')
const uploading = ref(false)
const fileOver = ref(false)
const editingSlug = ref(null)
const editTitle = ref('')
const editCategory = ref('')
const dragSlug = ref(null)
const overSlug = ref(null)
const overCategory = ref(null)
const addingCategory = ref(false)
const newCategory = ref('')
const collapsed = ref(loadCollapsed())

const UNCATEGORIZED = ''

// 카테고리 순서는 서버 목록을 따르고, 미분류는 맨 아래.
const groups = computed(() => {
  const byName = new Map(categoryNames.value.map((n) => [n, []]))
  const none = []
  for (const it of items.value) {
    if (it.category && byName.has(it.category)) byName.get(it.category).push(it)
    else none.push(it)
  }
  const result = [...byName.entries()].map(([name, list]) => ({ name, list }))
  result.push({ name: UNCATEGORIZED, list: none })
  return result
})
const dragging = computed(() => items.value.find((i) => i.slug === dragSlug.value) || null)

async function load() {
  try {
    const [list, cats] = await Promise.all([api.list(), api.categories()])
    items.value = list
    categoryNames.value = cats
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

// ---- 접기 / 펼치기 (브라우저에 저장) ----
function loadCollapsed() {
  try {
    return new Set(JSON.parse(localStorage.getItem('collapsed') || '[]'))
  } catch {
    return new Set()
  }
}
function toggle(name) {
  const next = new Set(collapsed.value)
  if (next.has(name)) next.delete(name)
  else next.add(name)
  collapsed.value = next
  try {
    localStorage.setItem('collapsed', JSON.stringify([...next]))
  } catch {}
}
const isCollapsed = (name) => collapsed.value.has(name)

// ---- 카테고리 추가 / 삭제 ----
function startAddCategory() {
  addingCategory.value = true
  newCategory.value = ''
}
function submitCategory() {
  const name = newCategory.value.trim()
  addingCategory.value = false
  if (!name) return
  run(() => api.addCategory(name))
}
function removeCategory(g) {
  const msg = g.list.length
    ? `"${g.name}" 카테고리를 지울까요? 안에 있는 파일 ${g.list.length}개는 카테고리 없음으로 옮겨집니다.`
    : `"${g.name}" 카테고리를 지울까요?`
  if (!confirm(msg)) return
  run(() => api.removeCategory(g.name))
}
const renamingCategory = ref(null)
const renameValue = ref('')
function startRenameCategory(name) {
  renamingCategory.value = name
  renameValue.value = name
}
function submitRenameCategory() {
  const old = renamingCategory.value
  const next = renameValue.value.trim()
  renamingCategory.value = null
  if (!old || !next || next === old) return
  run(async () => {
    await api.renameCategory(old, next)
    if (collapsed.value.has(old)) {
      toggle(old)
      toggle(next)
    }
  })
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
  const files = [...e.dataTransfer.files].filter((f) => /\.(zip|html?)$/i.test(f.name))
  if (files.length === 0) {
    error.value = 'zip 또는 html 파일만 올릴 수 있습니다.'
    return
  }
  uploading.value = true
  notice.value = `${files.length}개 올리는 중`
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

// ---- 항목 드래그: 순서 변경과 카테고리 이동 ----
function onDragStart(it, e) {
  dragSlug.value = it.slug
  e.dataTransfer.effectAllowed = 'move'
  e.dataTransfer.setData('text/plain', it.slug)
}
function onDragOverItem(it) {
  if (dragSlug.value && dragSlug.value !== it.slug) {
    overSlug.value = it.slug
    overCategory.value = null
  }
}
function onDragOverCategory(name) {
  if (dragSlug.value) {
    overCategory.value = name
    overSlug.value = null
  }
}
function clearDrag() {
  dragSlug.value = null
  overSlug.value = null
  overCategory.value = null
}
// 항목 위에 놓기: 그 항목 앞으로 이동, 카테고리도 따라간다.
function onDropOnItem(target) {
  const moving = dragging.value
  clearDrag()
  if (!moving || moving.slug === target.slug) return
  const list = items.value.filter((i) => i.slug !== moving.slug)
  list.splice(list.indexOf(target), 0, moving)
  commitMove(list, moving, target.category)
}
// 카테고리 헤더나 빈 카테고리에 놓기: 그 카테고리의 맨 뒤로 이동.
function onDropOnCategory(name) {
  const moving = dragging.value
  clearDrag()
  if (!moving) return
  const list = items.value.filter((i) => i.slug !== moving.slug)
  let at = list.length
  for (let i = list.length - 1; i >= 0; i--) {
    if ((list[i].category || '') === name) {
      at = i + 1
      break
    }
  }
  list.splice(at, 0, moving)
  commitMove(list, moving, name)
}
function commitMove(list, moving, category) {
  const categoryChanged = (moving.category || '') !== (category || '')
  items.value = list.map((i) => (i.slug === moving.slug ? { ...i, category } : i))
  run(async () => {
    await api.reorder(list.map((i) => i.slug))
    if (categoryChanged) await api.patch(moving.slug, { category })
  })
}
</script>

<template>
  <div class="page">
    <h1>발표자료</h1>

    <div v-if="error" class="error">{{ error }}</div>
    <div v-if="notice" class="hint">{{ notice }}</div>

    <div v-if="items.length === 0 && categoryNames.length === 0" class="empty">
      아직 올린 자료가 없습니다. html 파일이나 zip을 이 화면에 끌어다 놓으세요.
    </div>

    <section
      v-for="g in groups"
      :key="g.name || '__none'"
      class="category"
      :class="{ over: overCategory === g.name, uncategorized: g.name === UNCATEGORIZED, collapsed: isCollapsed(g.name) }"
      v-show="g.name !== UNCATEGORIZED || g.list.length > 0 || dragSlug"
      @dragover.prevent="onDragOverCategory(g.name)"
      @dragleave.self="overCategory = null"
      @drop.prevent.stop="onDropOnCategory(g.name)"
    >
      <h2 v-if="g.name" :class="{ renaming: renamingCategory === g.name }">
        <form v-if="renamingCategory === g.name" class="rename-form" @submit.prevent="submitRenameCategory">
          <input
            class="rename-cat"
            v-model="renameValue"
            autofocus
            @keydown.esc="renamingCategory = null"
            @blur="submitRenameCategory"
          />
        </form>
        <button v-else class="toggle" :aria-expanded="!isCollapsed(g.name)" @click="toggle(g.name)">
          <svg class="caret" :class="{ closed: isCollapsed(g.name) }" width="10" height="10" viewBox="0 0 10 10" aria-hidden="true">
            <path d="M2 3.5 L5 6.5 L8 3.5" fill="none" stroke="currentColor" stroke-width="1.4" stroke-linecap="round" stroke-linejoin="round" />
          </svg>{{ g.name }}
          <span v-if="isCollapsed(g.name) && g.list.length" class="count">{{ g.list.length }}</span>
        </button>
        <span v-if="renamingCategory !== g.name" class="cat-actions">
          <button class="ghost" @click="startRenameCategory(g.name)">수정</button>
          <button class="ghost danger" @click="removeCategory(g)">삭제</button>
        </span>
        <span class="rule" aria-hidden="true"></span>
      </h2>
      <h2 v-else-if="dragSlug && dragging && dragging.category" class="none-label">카테고리 없음<span class="rule" aria-hidden="true"></span></h2>

      <template v-if="!isCollapsed(g.name)">
        <div
          v-for="(it, idx) in g.list"
          :key="it.slug"
          class="item reveal"
          :style="{ '--i': idx }"
          :class="{ dragging: dragSlug === it.slug, over: overSlug === it.slug, editing: editingSlug === it.slug }"
          :draggable="editingSlug !== it.slug"
          @dragstart="onDragStart(it, $event)"
          @dragover.prevent.stop="onDragOverItem(it)"
          @drop.prevent.stop="onDropOnItem(it)"
          @dragend="clearDrag"
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
        <div v-if="g.name && g.list.length === 0" class="item placeholder">
          <span class="hint">{{ dragSlug ? '여기에 놓기' : '비어 있음. 파일을 끌어다 놓으세요.' }}</span>
        </div>
      </template>
    </section>
    <datalist id="cats"><option v-for="c in categoryNames" :key="c" :value="c" /></datalist>

    <div class="add-category">
      <form v-if="addingCategory" @submit.prevent="submitCategory">
        <input
          class="new-cat"
          v-model="newCategory"
          placeholder="카테고리 이름"
          autofocus
          @keydown.esc="addingCategory = false"
          @blur="submitCategory"
        />
      </form>
      <button v-else class="add" @click="startAddCategory">+ 카테고리 추가</button>
    </div>

    <p v-if="items.length > 0" class="hint footer">html 파일이나 zip을 끌어다 놓으면 올라갑니다. 같은 이름이면 덮어쓰고, 항목을 끌어 순서와 카테고리를 바꿀 수 있습니다.</p>

    <div v-if="fileOver" class="dropzone">
      <div>{{ uploading ? '올리는 중' : '놓으면 올라갑니다' }}</div>
    </div>
  </div>
</template>
