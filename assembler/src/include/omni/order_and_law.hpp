//***************************************************************************
//* Copyright (c) 2011-2012 Saint-Petersburg Academic University
//* All Rights Reserved
//* See file LICENSE for details.
//****************************************************************************

#pragma once

#include <ostream>
#include <unordered_set>
#include <unordered_map>
#include <stacktrace.hpp>

namespace restricted
{

template<class T>
	struct pure_pointer
{
	typedef T  type;
	typedef T* pointer_type;

	explicit pure_pointer(T *ptr = 0)
		: ptr_(ptr), int_id_(generate_id(ptr))
	{
	}

	T *get			() const 	{ return ptr_ ; }
	T& operator*	() const	{ return *ptr_;	}
	T* operator->	() const	{ return ptr_ ;	}

	bool operator==(const pure_pointer &rhs) const { return ptr_ == rhs.ptr_ && int_id_ == rhs.int_id_; }
	bool operator!=(const pure_pointer &rhs) const { return ptr_ != rhs.ptr_; }

	bool operator<(const pure_pointer &rhs) const {
		return this->int_id_ < rhs.int_id_;
	}

	size_t hash() const {
		return this->int_id_;
	}

	size_t int_id() const {
		return int_id_;
	}

private:

	static size_t generate_id(T *ptr) {
		if(ptr == 0 || ptr == (T*)1 || ptr == (T*)(-1)) {
			return size_t(ptr);
		}
		return get_new_int_id();
	}

	static size_t get_new_int_id() {
		static size_t max_int_id = 1;
		max_int_id++;
		return max_int_id;
	}

	T *ptr_;

	size_t int_id_;
};

//template<class T>
//struct Comparator
//{
//	typedef pure_pointer<T> pointer_type_t;
//
//	bool operator()(pointer_type_t const& a, pointer_type_t const& b) const {
//		return a.get() < b.get();
//	}
//};

template<class T>
struct Hash
{
	typedef pure_pointer<T> pointer_type_t;
	std::hash<T*> inner_hash_;

	size_t operator()(pointer_type_t const& a) const {
		return inner_hash_(a.get());
	}
};

template<class It>
struct iterator_wrapper
{
	typedef typename It::value_type 		value_type;
	typedef typename It::difference_type 	difference_type;
	typedef typename It::reference 			reference;
	typedef typename It::pointer   			pointer;

	explicit iterator_wrapper(It it) : it_(it) {}

	reference 	operator*	() const { return it_.operator* (); }
	pointer  	operator->	() const { return it_.operator->(); }

	bool operator==(const iterator_wrapper &rhs) const { return it_ == rhs.it_; }
	bool operator!=(const iterator_wrapper &rhs) const { return it_ != rhs.it_; }

private:
	It it_;
};

template<class T>
struct set
{
	typedef Hash<typename T::type> hash_t;
	typedef std::unordered_set<T, hash_t> base_set_t;
	typedef typename base_set_t::value_type value_type;

	typedef iterator_wrapper<typename base_set_t::iterator			>	iterator;
	typedef iterator_wrapper<typename base_set_t::const_iterator	>	const_iterator;

public:
	set()
		: base_set_(10, hash_t())
	{
	}

	template<class It>
	set(It begin, It end)
		: base_set_(begin, end, 10, hash_t())
	{
	}

	const_iterator 	begin() const	{ return const_iterator(base_set_.begin()); }
	const_iterator	end	 () const	{ return const_iterator(base_set_.end  ()); }

	iterator     	begin() 		{ return iterator(base_set_.begin()); }
	iterator 		end  () 		{ return iterator(base_set_.end  ()); }

	const_iterator 	find	(const T &key) const{ return  const_iterator(base_set_.find(key)); }
	iterator 		find 	(const T &key) 		{ return 		iterator(base_set_.find(key)); }

	size_t count(T const& item) const { return base_set_.count(item); }

	std::pair<iterator, bool> insert(value_type const& item)
	{
		std::pair<iterator, bool> ret = base_set_.insert(item);
		return make_pair(iterator(ret.first), ret.second);
	}

	template<class It>
	void 	insert(It first, It last)	{ base_set_.insert(first, last); }

	size_t 	erase (const T& x)			{ return base_set_.erase(x); 	 }
	void 	clear ()					{ base_set_.clear();			 }
	size_t 	size  () const				{ return base_set_.size();		 }

	bool operator==(const set &rhs) const
	{
		if(this->size() != rhs.size())
			return false;

		for(auto i = base_set_.begin(), j = rhs.base_set_.begin();
			i != base_set_.end() && j != rhs.base_set_.end();
			++i, ++j)
		{
			if(*i != *j)
				return false;
		}

		return true;
	}

	bool operator!=(const set &rhs) const
	{
		return !(*this == rhs);
	}

	template<class Comparator>
	void Copy(std::set<T, Comparator> &container) const {
		container.insert(base_set_.begin(), base_set_.end());
	}

private:
	base_set_t base_set_;
};


template<class Key, class Value>
struct map
{
	typedef Hash<typename Key::type> hash_t;
	typedef std::unordered_map<Key, Value, hash_t> base_map_t;
	typedef typename base_map_t::value_type value_type;

	typedef iterator_wrapper<typename base_map_t::iterator		>	iterator;
	typedef iterator_wrapper<typename base_map_t::const_iterator>	const_iterator;

public:
	map()
		: base_map_(10, hash_t())
	{
	}

	template<class It>
	map(It begin, It end)
		: base_map_(begin, end, 10, hash_t())
	{
	}

	const_iterator 	begin() const 	{ return const_iterator(base_map_.begin()); }
	const_iterator	end	 () const 	{ return const_iterator(base_map_.end  ()); }

	iterator     	begin() 	 	{ return iterator(base_map_.begin()); }
	iterator 		end  () 		{ return iterator(base_map_.end  ()); }

	const_iterator 	find	(const Key &key) const
	{
		return const_iterator(base_map_.find(key));
	}
	iterator 		find 	(const Key &key) 		{ return 		iterator(base_map_.find(key)); }

	size_t count(Key const& item) const { return base_map_.count(item); }

	Value& operator[](Key const& x) { return base_map_[x]; }

	std::pair<iterator, bool> insert(value_type const& value)
	{
		std::pair<iterator, bool> ret = base_map_.insert(value);
		return make_pair(iterator(ret.first), ret.second);
	}

	template<class It>
	void 	insert(It first, It last)	{ base_map_.insert(first, last); }
	size_t 	erase (Key const& x)		{ return base_map_.erase(x);	}
	void 	clear ()					{ base_map_.clear();			}

	size_t 	size  () const				{ return base_map_.size();		}

	bool operator==(const map &rhs) const
	{
		if(size() != rhs.size())
			return false;

		for(auto i = base_map_.begin(), j = rhs.base_map_.begin();
			i != base_map_.end() && j != rhs.base_map_.end();
			++i, ++j)
		{
			if(*i != *j)
				return false;
		}

		return true;
	}

	bool operator!=(const map& rhs) const
	{
		return !(*this == rhs);
	}

	template<class Comparator>
	void Copy(std::map<Key, Value, Comparator> &container) const {
		container.insert(base_map_.begin(), base_map_.end());
	}

private:
	base_map_t base_map_;
};

template<class T>
ostream &operator<<(ostream &stream, const pure_pointer<T>& pointer)
{
	stream << pointer.get();
	return stream;
}

} // namespace restricted

namespace std
{
template<class T>
struct hash<restricted::pure_pointer<T>> {
	size_t operator()(const restricted::pure_pointer<T>& pointer) const {
		return pointer.hash();
	}
};
}

template<class T, class Comparator>
class PairComparator {
private:
	Comparator comparator_;
public:
	PairComparator(Comparator comparator) : comparator_(comparator) {
	}

	bool operator()(std::pair<T, T> a, std::pair<T, T> b) const {
		return a.first == b.first ? comparator_(a.second, b.second) : comparator_(a.first, b.first);
	}
};

//
//template<typename T, class Comparator>
//class MixedComparator {
//private:
//	Comparator c1_;
//	Comparator c2_;
//public:
//	MixedComparator(const Comparator &c1, const Comparator &c2) : c1_(c1), c2_(c2) {
//	}
//
//	bool operator()(const T &a, const T &b) const {
//		if(c1_.IsAFAKE(a) || c1_.IsAFAKE(b)) {
//			if(c1_.IsAFAKEMin(a))
//				return !c1_.IsAFAKEMin(b);
//			if(c1_.IsAFAKEMax(b))
//				return c1_.IsAFAKEMax(a);
//			return false;
//		}
//		if(c1_.IsValidId(a) && c1_.IsValidId(b))
//			return c1_(a, b);
//		if(c1_.IsValidId(a))
//			return true;
//		if(c1_.IsValidId(b))
//			return false;
//		if(c2_.IsValidId(a) && c2_.IsValidId(b)) {
//			return c2_(a, b);
//		}
//		VERIFY(false);
//		return false;
//	}
//
//	bool IsValidId(T element) {
//		return c1_.IsValid(element) || c2_.IsValid(element);
//	}
//};

template<class Container, class Comparator>
class ContainerComparator {
private:
	Comparator comparator_;
public:
	ContainerComparator(const Comparator &comparator) : comparator_(comparator) {
	}

	bool operator()(const Container &a, const Container &b) const {
		for(auto ita = a.begin, itb = b.begin(); ita != a.end() && itb != b.end(); ++ita, ++itb) {
			if(*ita != *itb)
				return comparator_(*ita, *itb);
		}
		if(a.size() < b.size()) {
			return true;
		}
		return false;
	}

};

