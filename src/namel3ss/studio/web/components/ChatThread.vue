<template>
  <section class="n3-chat-thread" role="log" aria-live="polite">
    <header class="n3-chat-thread-header">
      <slot name="title">Chat Thread</slot>
    </header>
    <article
      v-for="message in messages"
      :key="message.id"
      class="n3-chat-message"
      :data-role="message.role"
      :data-status="message.status || 'complete'"
    >
      <p class="n3-chat-content">{{ message.content }}</p>
      <ul v-if="message.citations && message.citations.length" class="n3-chat-citations">
        <li v-for="citation in message.citations" :key="citation" class="n3-chat-citation">{{ citation }}</li>
      </ul>
    </article>
    <div v-if="streaming" class="n3-chat-streaming">Streaming...</div>
  </section>
</template>

<script>
export default {
  name: "ChatThread",
  props: {
    messages: {
      type: Array,
      default: () => [],
    },
    streaming: {
      type: Boolean,
      default: false,
    },
  },
};
</script>

<style scoped>
.n3-chat-thread {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.n3-chat-thread-header {
  font-weight: 600;
}

.n3-chat-message {
  border: 1px solid #e5e5e5;
  border-radius: 10px;
  padding: 8px;
}

.n3-chat-message[data-role="assistant"] {
  background: #f8fafc;
}

.n3-chat-content {
  margin: 0;
}

.n3-chat-citations {
  margin: 6px 0 0;
  padding-left: 18px;
}

.n3-chat-streaming {
  font-size: 12px;
  color: #555;
}
</style>
