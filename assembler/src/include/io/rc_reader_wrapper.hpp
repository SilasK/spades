//***************************************************************************
//* Copyright (c) 2011-2013 Saint-Petersburg Academic University
//* All Rights Reserved
//* See file LICENSE for details.
//****************************************************************************

/**
 * @file    rc_reader_wrapper.hpp
 * @author  Mariya Fomkina
 * @version 1.0
 *
 * @section LICENSE
 *
 * This program is free software; you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation; either version 2 of
 * the License, or (at your option) any later version.
 *
 * @section DESCRIPTION
 *
 * RCReaderWrapper is the class-wrapper that gets reads and reverse
 * complimentary reads from given reader (one by one).
 */

#pragma once

#include <boost/noncopyable.hpp>
#include <boost/foreach.hpp>

#include "ireader.hpp"
#include "read_stream_vector.hpp"

namespace io {

template<typename ReadType>
class RCReaderWrapper: public IReader<ReadType> {
public:
	/*
	 * Default constructor.
	 *
	 * @param reader Reference to any other reader (child of IReader).
	 */
	explicit RCReaderWrapper(IReader<ReadType>& reader) :
			reader_(reader), rc_read_(), was_rc_(true) {
	}

	/*
	 * Check whether the stream is opened.
	 *
	 * @return true of the stream is opened and false otherwise.
	 */
	/* virtual */
	bool is_open() {
		return reader_.is_open();
	}

	/*
	 * Check whether we've reached the end of stream.
	 *
	 * @return true if the end of stream is reached and false
	 * otherwise.
	 */
	/* virtual */
	bool eof() {
		return (was_rc_) && (reader_.eof());
	}

	/*
	 * Read SingleRead or PairedRead from stream (according to ReadType).
	 *
	 * @param read The SingleRead or PairedRead that will store read
	 * data.
	 *
	 * @return Reference to this stream.
	 */
	/* virtual */
	RCReaderWrapper& operator>>(ReadType& read) {
		if (was_rc_) {
			reader_ >> read;
			rc_read_ = read;
		} else {
			read = !rc_read_;
		}
		was_rc_ = !was_rc_;
		return (*this);
	}

	/*
	 * Close the stream.
	 */
	/* virtual */
	void close() {
		reader_.close();
	}

	/*
	 * Close the stream and open it again.
	 */
	/* virtual */
	void reset() {
		was_rc_ = true;
		reader_.reset();
	}

	ReadStat get_stat() const {
		ReadStat stat = reader_.get_stat();
		stat.merge(stat);
		return stat;
	}

private:
	/*
	 * @variable Internal stream readers.
	 */
	IReader<ReadType>& reader_;
	/*
	 * @variable Last read got from the stream.
	 */
	ReadType rc_read_;
	/*
	 * @variable Flag that shows where reverse complimentary copy of the
	 * last read read was already outputted.
	 */
	bool was_rc_;

};

//todo what is this?
template<typename ReadType>
class CleanRCReaderWrapper: public IReader<ReadType> {
public:
	/*
	 * Default constructor.
	 *
	 * @param reader Reference to any other reader (child of IReader).
	 */
	explicit CleanRCReaderWrapper(IReader<ReadType>* reader) :
			reader_(reader), rc_read_(), was_rc_(true) {
	}

	/*
	 * Default destructor.
	 */
	/* virtual */
	~CleanRCReaderWrapper() {
		delete reader_;
	}

	/*
	 * Check whether the stream is opened.
	 *
	 * @return true of the stream is opened and false otherwise.
	 */
	/* virtual */
	bool is_open() {
		return reader_->is_open();
	}

	/*
	 * Check whether we've reached the end of stream.
	 *
	 * @return true if the end of stream is reached and false
	 * otherwise.
	 */
	/* virtual */
	bool eof() {
		return (was_rc_) && (reader_->eof());
	}

	/*
	 * Read SingleRead or PairedRead from stream (according to ReadType).
	 *
	 * @param read The SingleRead or PairedRead that will store read
	 * data.
	 *
	 * @return Reference to this stream.
	 */
	/* virtual */
	CleanRCReaderWrapper& operator>>(ReadType& read) {
		if (was_rc_) {
			reader_->operator >>(read);
			rc_read_ = read;
		} else {
			read = !rc_read_;
		}
		was_rc_ = !was_rc_;
		return (*this);
	}

	/*
	 * Close the stream.
	 */
	/* virtual */
	void close() {
		reader_->close();
	}

	/*
	 * Close the stream and open it again.
	 */
	/* virtual */
	void reset() {
		was_rc_ = true;
		reader_->reset();
	}

	ReadStat get_stat() const {
		ReadStat stat = reader_->get_stat();
		stat.merge(stat);
		return stat;
	}

private:
	/*
	 * @variable Internal stream readers.
	 */
	IReader<ReadType> * reader_;
	/*
	 * @variable Last read got from the stream.
	 */
	ReadType rc_read_;
	/*
	 * @variable Flag that shows where reverse complimentary copy of the
	 * last read read was already outputted.
	 */
	bool was_rc_;
};

template<class Reader>
std::shared_ptr<ReadStreamVector<Reader>> RCWrapStreams(ReadStreamVector<Reader>& streams) {
    auto/*std::shared_ptr<ReadStreamVector<Reader>>*/ rc_streams/*(new ReadStreamVector<Reader>());*/= std::make_shared<ReadStreamVector<Reader>>();
    BOOST_FOREACH(Reader& stream, streams) {
        rc_streams->push_back(new RCReaderWrapper<typename Reader::read_type>(stream));
    }
    return rc_streams;
}

}
