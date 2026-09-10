<script setup>
import { onMounted, ref } from 'vue'
import { api } from './api'
import Login from './Login.vue'
import List from './List.vue'

const state = ref('loading')

onMounted(async () => {
  try {
    await api.me()
    state.value = 'in'
  } catch {
    state.value = 'out'
  }
})
</script>

<template>
  <Login v-if="state === 'out'" @done="state = 'in'" />
  <List v-else-if="state === 'in'" @logout="state = 'out'" />
</template>
