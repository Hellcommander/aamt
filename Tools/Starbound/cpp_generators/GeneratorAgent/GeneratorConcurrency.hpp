#pragma once

/**
 * Concurrency helpers shared by the GeneratorAgent asset factories:
 *  - ConcurrentLRUCache<K, V>: thread-safe LRU cache with hit statistics
 *    (find() returns std::optional<V>, so `if (auto hit = cache.find(k)) use(*hit);`).
 *  - GeneratorTaskPool: fixed worker pool whose enqueue() returns a std::future.
 */

#include "core/ConcurrentLRU.hpp"
#include <atomic>
#include <condition_variable>
#include <cstddef>
#include <deque>
#include <functional>
#include <future>
#include <memory>
#include <mutex>
#include <optional>
#include <stdexcept>
#include <thread>
#include <type_traits>
#include <vector>

namespace MagiTech {

template <typename K, typename V>
class ConcurrentLRUCache {
public:
    explicit ConcurrentLRUCache(size_t capacity = 256) : m_lru(capacity) {}

    void set_capacity(size_t capacity) { m_lru.setMaxSize(capacity == 0 ? 1 : capacity); }
    void init(size_t capacity) { set_capacity(capacity); clear(); }
    size_t capacity() const { return m_lru.getMaxSize(); }
    size_t size() const { return m_lru.size(); }

    std::optional<V> find(const K& key) {
        auto value = m_lru.get(key);
        (value ? m_hits : m_misses).fetch_add(1, std::memory_order_relaxed);
        return value;
    }
    bool contains(const K& key) const { return m_lru.contains(key); }
    void insert(const K& key, const V& value) { m_lru.put(key, value); }
    bool erase(const K& key) { return m_lru.remove(key); }
    void clear() {
        m_lru.clear();
        m_hits = 0;
        m_misses = 0;
    }

    /** Fraction of find() calls that hit, 0 when nothing was looked up yet. */
    double getHitRate() const {
        const double hits = static_cast<double>(m_hits.load());
        const double total = hits + static_cast<double>(m_misses.load());
        return total > 0.0 ? hits / total : 0.0;
    }

private:
    ConcurrentLRU<K, V> m_lru;
    std::atomic<uint64_t> m_hits{0};
    std::atomic<uint64_t> m_misses{0};
};

class GeneratorTaskPool {
public:
    GeneratorTaskPool() = default;
    explicit GeneratorTaskPool(size_t threads) { start(threads); }
    ~GeneratorTaskPool() { stop(); }

    GeneratorTaskPool(const GeneratorTaskPool&) = delete;
    GeneratorTaskPool& operator=(const GeneratorTaskPool&) = delete;

    void start(size_t threads) {
        std::lock_guard<std::mutex> lock(m_mutex);
        if (!m_workers.empty()) return;
        m_stopping = false;
        const size_t count = threads == 0 ? std::max(1u, std::thread::hardware_concurrency()) : threads;
        for (size_t i = 0; i < count; ++i) {
            m_workers.emplace_back([this] { workerLoop(); });
        }
    }

    /** Finishes queued tasks, then joins the workers. */
    void stop() {
        {
            std::lock_guard<std::mutex> lock(m_mutex);
            if (m_workers.empty()) return;
            m_stopping = true;
        }
        m_cv.notify_all();
        for (auto& worker : m_workers) {
            if (worker.joinable()) worker.join();
        }
        std::lock_guard<std::mutex> lock(m_mutex);
        m_workers.clear();
    }

    size_t size() const {
        std::lock_guard<std::mutex> lock(m_mutex);
        return m_workers.size();
    }

    /** Runs `fn(args...)` on a worker (inline when the pool was never started). */
    template <typename F, typename... Args>
    auto enqueue(F&& fn, Args&&... args) -> std::future<std::invoke_result_t<std::decay_t<F>, std::decay_t<Args>...>> {
        using R = std::invoke_result_t<std::decay_t<F>, std::decay_t<Args>...>;
        auto task = std::make_shared<std::packaged_task<R()>>(
            [f = std::forward<F>(fn), ... a = std::forward<Args>(args)]() mutable { return std::invoke(f, a...); });
        std::future<R> result = task->get_future();
        bool runInline = false;
        {
            std::lock_guard<std::mutex> lock(m_mutex);
            if (m_workers.empty()) {
                runInline = true;
            } else {
                m_queue.emplace_back([task] { (*task)(); });
            }
        }
        if (runInline) {
            // No workers (not started / stopped): execute synchronously so callers still get a value
            (*task)();
        } else {
            m_cv.notify_one();
        }
        return result;
    }

private:
    void workerLoop() {
        for (;;) {
            std::function<void()> job;
            {
                std::unique_lock<std::mutex> lock(m_mutex);
                m_cv.wait(lock, [this] { return m_stopping || !m_queue.empty(); });
                if (m_queue.empty()) return;   // stopping and drained
                job = std::move(m_queue.front());
                m_queue.pop_front();
            }
            job();
        }
    }

    mutable std::mutex m_mutex;
    std::condition_variable m_cv;
    std::deque<std::function<void()>> m_queue;
    std::vector<std::thread> m_workers;
    bool m_stopping = false;
};

} // namespace MagiTech
