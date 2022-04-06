import logging
import marshal
import os
import reprlib
from contextlib import contextmanager
from ctypes import Structure, c_bool, c_int32, c_int64, c_ssize_t
from multiprocessing import Lock, RawValue, RawArray
from multiprocessing.shared_memory import SharedMemory
from time import time


_logger = logging.getLogger(__name__)

AVG_SIZE_OF_DATA = 4096

class LockIdentify:
    """
    Lock where the pid is save into a Shared Value to be able to release the lock
    from a other Process (parent process)
    """
    def __init__(self) -> None:
        self._lock = Lock()
        self._pid = RawValue(c_int64, -1)

    def __enter__(self):
        # CRITICAL SECTION: if the process is killed after the acquire
        # but before set the pid, the _lock is locked without knowing
        # which one take it, then the PreforkServer cannot release it
        self._lock.acquire()
        self._pid.value = os.getpid()

    def __exit__(self, exc_type, exc_val, exc_tb):
        # CRITICAL SECTION: if the process is killed after reset the pid
        # but before release, the _lock is locked without knowing
        # which one take it, then the PreforkServer cannot release it
        self._pid.value = -1
        self._lock.release()

    def release_if_mandatory(self, pid):
        """Release the lock if it is locked by the process with `pid`

        Args:
            pid (int): pid of a killed process
        """
        res = self._lock.acquire(block=False)
        if not res and self._pid.value == pid:
            _logger.info("Force the release of SM lock for pid=%s", pid)
            self._pid.value = -1
            self._lock.release()
        elif res:
            self._lock.release()

class _Entry(Structure):
    """
    Hash LRU Table entry structure
    """
    _fields_ = [
        ("hash", c_ssize_t),
        ("prev", c_int32),
        ("next", c_int32),
    ]

    def __str__(self) -> str:
        return f"hash={self.hash}, prev={self.prev}, next={self.next}"
    __repr__ = __str__

class _DataIndex(Structure):
    _fields_ = [
        ("position", c_int64),
        ("size", c_int64),  # TODO: maybe `end` instead, to avoid useless concat
    ]

    def __str__(self) -> str:
        return f"position={self.position}, size={self.size}"
    __repr__ = __str__

class SharedMemoryLRU:
    def __init__(self, size=4096):
        byte_size = size * AVG_SIZE_OF_DATA
        _logger.debug("Create Shared Memory of %d bytes", byte_size)

        self._lock = LockIdentify()
        self._sm = SharedMemory(size=byte_size, create=True)
        # self._sm.buf[:] = b'\x00' * byte_size

        self._size = size

        # We cannot take more that 10 % of memory with one data (TODO)
        self._max_size_one_data = byte_size // 10
        # `self._max_length` should be always < than size.
        # bigger it is, more there are hash conflict, and then slow down the `_lookup` but increase the memory cost
        self._max_length = size // 2

        self._consistent = RawValue(c_bool, True)
        self._head = RawArray(c_int32, [-1, 0, 1])  # root, length, free_len
        self._entry_table = RawArray(_Entry, [(0, -1, -1)] * size)
        self._data_idx = RawArray(_DataIndex, [(-1, -1)] * size)
        self._data_free = RawArray(_DataIndex, [(-1, -1)] * size)
        self._data_free[0] = (0, self._sm.size)
        self._data = self._sm.buf

    _root = property(lambda self: self._head[0], lambda self, x: self._head.__setitem__(0, x))
    _length = property(lambda self: self._head[1], lambda self, x: self._head.__setitem__(1, x))
    _free_len = property(lambda self: self._head[2], lambda self, x: self._head.__setitem__(2, x))

    def _check_consistence(self):
        """ Check that the last change of the SharedMemory was consistent

        ! Need lock !
        """
        if not self._consistent.value:
            _logger.info("Shared Memory not consistent, clean it")
            self._head[:] = [-1, 0, 1]
            self._entry_table[:] = [(0, -1, -1)] * self._size
            self._data_idx[:] = [(-1, -1)] * self._size
            self._data_free[:] = [(-1, -1)] * self._size
            self._data_free[0] = (0, self._sm.size)
            self._consistent.value = True

    def _defrag(self):
        """
        Defragment the `self._data`, it will result only one block of free fragment.
        The `self._entry_table` should be already update to avoid defragment

        O(log(n) * n), n is `self._max_length` (due to `sorted`)

        ! Need lock !
        """
        _logger.debug("Defragment the shared memory, nb fragment = %d", self._free_len)
        s = time()
        # Filtered out unused index and sorted by position to ensure that the defragmentation won't override any data
        current_position = 0
        used_indices = filter(lambda i: self._entry_table[i].prev != -1 and self._data_idx[i].position != -1, range(self._size))
        sorted_indexes = sorted(used_indices, key=lambda i: self._data_idx[i].position)
        for i in sorted_indexes:
            data_entry = self._data_idx[i]
            self._data[current_position:current_position + data_entry.size] = self._data[data_entry.position:data_entry.position + data_entry.size]
            data_entry.position = current_position
            current_position += data_entry.size
        self._data_free[0] = (current_position, self._sm.size - current_position)
        self._free_len = 1
        _logger.debug("Defragment the shared memory in %.4f ms, remaining free space : %s", (time() - s), self._data_free[0])

    def _malloc(self, data):
        """
        Reserved a free slot of shared memory for the root entry,
        insert data into and keep track of this spot.
        If there isn't enough memory, pop min(10% of entry, enough for this data) and _defrag

        ! Need lock !
        """
        size = len(data)
        nb_free_byte = 0
        for i in range(self._free_len):
            data_free_entry = self._data_free[i]
            if data_free_entry.size >= size:
                break
            nb_free_byte += data_free_entry.size
        else:
            if nb_free_byte < size:
                # If nb_free_byte isn't enough,
                # We pop existing data until we have enough memory
                for i in range(self._length):
                    if nb_free_byte >= size and i > self._length // 10:
                        # At minimum remove 10% of the memory to avoid to many defrag when memory is the bottleneck
                        break
                    nb_free_byte += self._lru_pop()
                else:
                    raise MemoryError("Your max_size_one_data is > size_byte, it shouldn't happen")
                _logger.debug("Pop %s items to be handle to add the new item", i + 1)

            self._defrag()
            data_free_entry = self._data_free[0]

        mem_pos = data_free_entry.position
        self._data[mem_pos:(mem_pos + size)] = data
        # We restrict _malloc for the root entry only,
        # because a index can already change because of the lru_pop before
        self._data_idx[self._root] = (mem_pos, size)
        data_free_entry.size -= size
        data_free_entry.position += size

    def _free(self, index):
        """
        It is the opposite of _malloc. Free the memory used by entry at `index`
        Also, it launch sometime the _defrag if:
            - No more entry to register free position entry
            - The first free slot is too _small (heuristic: _small = AVG_SIZE_OF_DATA)

        ! Need lock !
        """
        last = self._free_len
        self._data_free[last] = self._data_idx[index]
        free_size = self._data_free[last].size
        new_free_len = last + 1
        self._data_idx[index] = (-1, -1)
        # If the first free slot is too _small (heuristic: _small = AVG_SIZE_OF_DATA) and there are lot of fragment to retrieve:
        # -> We should _defrag to get a efficient _malloc
        # Also _defrag directly if there isn't any place in self._data_free
        if (self._data_free[0].size < AVG_SIZE_OF_DATA and new_free_len > self._size // 10) or new_free_len >= self._size:
            # It will result that self._free_len == 1
            self._defrag()
        else:
            self._free_len = new_free_len

        return free_size  # Return the size freed

    def _lru_pop(self):
        """
        Remove the last entry/data used (approximately for now,
        because doesn't update lru if not acquire write lock)

        ! Need lock !
        """
        if self._root == -1:
            raise Exception(f"Try to pop from empty lru ({self._length})")
        prev_index = self._entry_table[self._root].prev
        return self._del_index(prev_index, self._entry_table[prev_index])

    def _del_index(self, index, entry):
        """
        Remove the entry at `index` and data linked to.
        It compacts the hash table to ensure the correctness
        of the _lookup (linear probing)

        ! Need lock !
        """
        if entry.prev == entry.next == index:  # If am the only one
            self._root = -1
        else:
            self._entry_table[entry.next].prev = entry.prev
            self._entry_table[entry.prev].next = entry.next
            if self._root == index:
                self._root = entry.next

        self._entry_table[index] = (0, -1, -1)
        self._length -= 1
        free_size = self._free(index)

        # Delete the keys that are between this element, and the next free spot, having
        # an index lower or equal to the position we delete (conflicts handling).
        def move_index(old_index, new_index):
            old_entry = self._entry_table[old_index]
            hash_i, prev_i, next_i = old_entry.hash, old_entry.prev, old_entry.next
            if self._entry_table[old_index].next == old_index:  # if it is the only one item
                prev_i = next_i = new_index
            self._entry_table[prev_i].next = self._entry_table[next_i].prev = new_index
            self._entry_table[new_index] = (hash_i, prev_i, next_i)
            self._entry_table[old_index] = (0, -1, -1)
            self._data_idx[new_index] = self._data_idx[old_index]
            self._data_idx[old_index] = (-1, -1)
            if self._root == old_index:
                self._root = new_index

        index_empty = index
        for i in range(index + 1, index + self._size):
            i_mask = i % self._size  # from index -> self._size -> 0 -> index - 1
            i_entry = self._entry_table[i_mask]
            if i_entry.prev == -1:
                break
            hash_mask = i_entry.hash % self._size

            distance_i = i_mask - hash_mask if i_mask >= hash_mask else self._size - hash_mask + i_mask
            # distance error of i,
            # - if 0 then he is a the correct location don't move
            # - if < than distance_new = not suitable location
            # else compress
            if distance_i == 0:
                continue
            distance_new = index_empty - hash_mask if index_empty >= hash_mask else self._size - hash_mask + index_empty
            if distance_new < distance_i:
                move_index(i_mask, index_empty)
                index_empty = i_mask
        else:
            raise MemoryError("The hashtable seems full, it doesn't make any sense")

        return free_size

    def _data_get(self, index):
        """
        Get (key, value) of entry at `index`.

        ! Need lock !
        """
        data_id = self._data_idx[index]
        return marshal.loads(self._data[data_id.position:data_id.position + data_id.size])

    def _lookup(self, key, hash_):
        """
        Return the first (index, entry, value) corresponding to (key, hash).
        If a entry is found, the value is set else it is None.

        ! Need lock !
         """
        for i in range(self._size):
            index = (hash_ + i) % self._size
            entry = self._entry_table[index]
            if entry.prev == -1:
                return index, entry, None
            if entry.hash == hash_:
                key_full, val = self._data_get(index)
                if key_full == key:  # Hash conflict is rare, then it is ok to load to much some time.
                    return index, entry, val
        raise MemoryError("Hash table full, doesn't make any sense, LRU is broken")

    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default

    def __getitem__(self, key):
        hash_ = hash(key)
        with self._lock:
            self._check_consistence()
            index, entry, val = self._lookup(key, hash_)
            if val is None:
                raise KeyError(f"{key} doesn't not exist")

            self._consistent.value = False
            if self._root != index:
                # Pop me from my previous location
                self._entry_table[entry.prev].next = entry.next
                self._entry_table[entry.next].prev = entry.prev
                # Put me in front
                entry.next = self._root
                entry.prev = self._entry_table[self._root].prev
                self._entry_table[self._entry_table[self._root].prev].next = index
                self._entry_table[self._root].prev = index
                self._root = index
            self._consistent.value = True
        return val

    def __setitem__(self, key, value):
        hash_ = hash(key)
        data = marshal.dumps((key, value))
        if len(data) > self._max_size_one_data:
            raise MemoryError(f"Too big object ({len(data)}) to put in the Shared Memory (max {self._max_size_one_data} bytes by entry)")

        with self._lock:
            self._check_consistence()
            index, entry, val = self._lookup(key, hash_)
            self._consistent.value = False
            if self._root == index:  # If I am already the root, just update the hash
                self._entry_table[index].hash = hash_
            else:
                if val is not None:  # Remove previous spot if exist
                    self._entry_table[entry.prev].next = entry.next
                    self._entry_table[entry.next].prev = entry.prev
                if self._root == -1:  # First item set
                    self._entry_table[index] = (hash_, index, index)
                else:
                    old_root_i = self._root
                    self._entry_table[index] = (hash_, self._entry_table[old_root_i].prev, old_root_i)
                    self._entry_table[self._entry_table[old_root_i].prev].next = index
                    self._entry_table[old_root_i].prev = index
                self._root = index

            if val is None:
                self._length += 1
            else:
                self._free(index)
            self._malloc(data)  # Malloc use root entry to find index

            if self._length > self._max_length:
                self._lru_pop()  # Make it after to avoid modifying index
            self._consistent.value = True

    # --------- Close methods

    def close(self):
        _logger.debug("Close shared memory")
        self._sm.close()

    def unlink(self):
        _logger.debug("Delete shared memory")
        self.close()
        del self._head, self._entry_table, self._data_idx, self._data_free, self._data, self._lock
        self._sm.unlink()
        del self

    # --------------------- TESTING methods ---------------

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unlink()

    def __len__(self):
        with self._lock:
            return self._length

    def __contains__(self, key):
        try:
            self[key]
        except KeyError:
            return False
        return True

    def __delitem__(self, key):
        hash_ = hash(key)
        with self._lock:
            self._check_consistence()
            index, entry, val = self._lookup(key, hash_)
            if val is None:
                raise KeyError(f"{key} doesn't not exist, cannot delete it")
            self._del_index(index, entry)

    # --------------------- DEBUGGING Methods --------------

    def __iter__(self):
        """ Only use for debugging"""
        # with self._lock:
        if self._root == -1:
            return
        node_index = self._root
        for _ in range(self._length + 1):
            yield self._data_get(node_index)
            node_index = self._entry_table[node_index].next
            if node_index == self._root:
                break
        else:
            raise MemoryError(f"Infinite loop detected in the Linked list, {self._root=}:\n" + "\n".join(str(i) + ": " + str(e) for i, e in enumerate(self._entry_table)))

    def __repr__(self) -> str:
        """ Only use for debugging"""
        result = []
        # with self._lock:
        if self._root == -1:
            return f'hashtable size: {self._size}, len: {str(self._length)}\n' + '\n'.join(result) + '\n' + "\n".join(str(e) for e in self._data_free)
        node_index = self._root
        for _ in range(self._length + 1):
            hash_key, nxt = self._entry_table[node_index].hash, self._entry_table[node_index].next
            try:
                data = self._data_get(node_index)
            except (ValueError, EOFError):
                data = ("<unable to read>", "<unable to read>")
            result.append(f'key: {data[0]}, hash % size: {hash_key % self._size}, index: {node_index}, {self._entry_table[node_index]}, data_pos={self._data_idx[node_index].position} - data_size={self._data_idx[node_index].size}: {reprlib.repr(data[1])}')
            node_index = nxt
            if node_index == self._root:
                return f'hashtable size: {self._size}, len: {str(self._length)}, {self._root=}\n' + \
                    '\n'.join(result) + \
                    f'\nFree spots {self._free_len}:\n' + \
                    "\n".join(str(e) for e in self._data_free[:self._free_len])
        raise MemoryError(f"Infinite loop detected in the Linked list, {self._root=}:\n" + "\n".join(str(i) + ": " + str(e) for i, e in enumerate(self._entry_table)))
