<script setup>
import { ref } from 'vue'
import Login from './Login.vue'
import List from './List.vue'

// 화면을 열 때마다 비밀번호를 묻는다. 이전 로그인 상태를 자동으로 확인하지 않는다.
const state = ref('out')
</script>

<template>
  <Login v-if="state === 'out'" @done="state = 'in'" />
  <List v-else @logout="state = 'out'" />
</template>
