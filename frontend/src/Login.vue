<script setup>
import { ref } from 'vue'
import { api } from './api'

const emit = defineEmits(['done'])
const password = ref('')
const error = ref('')
const busy = ref(false)

async function submit() {
  error.value = ''
  busy.value = true
  try {
    await api.login(password.value)
    emit('done')
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <form class="center" @submit.prevent="submit">
    <div class="login">
      <h1>발표자료</h1>
      <input class="field" type="password" v-model="password" placeholder="비밀번호" autofocus />
      <div><button class="go" :disabled="busy || !password">들어가기</button></div>
      <div v-if="error" class="error">{{ error }}</div>
    </div>
  </form>
</template>
